"""Flujo de datos: inspeccionar → validar → limpiar → analizar → guardar.

Todas las funciones reciben datos ya cargados (listas de diccionarios), así
no dependen de si el archivo original era CSV o JSON.
"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from src.modelos import (PENALES_REGLAMENTARIOS, Arquero, Equipo, Pateador,
                         TandaHistorica, a_probabilidad, esta_vacio)
from src.simulacion import (equipo_homogeneo, intervalo_proporcion,
                            simular_enfrentamiento)

COLUMNAS_HISTORICO = set(TandaHistorica.CAMPOS)
COLUMNAS_PLANTELES = {"codigo_equipo", "equipo", "rol", "nombre",
                      "efectividad", "temple", "factor_atajada"}
TEMPLE_POR_DEFECTO = 0.5   # temple neutro si el dato falta
TIROS_TRAMO_FINAL = 14     # en la comparación, 14 o más tiros van juntos


# --- Inspección y esquema --------------------------------------------------
def inspeccionar(filas):
    """Describe lo que se leyó: registros, columnas, tipos y vacíos."""
    columnas = []
    for fila in filas:
        for columna in fila:
            if columna not in columnas:
                columnas.append(columna)
    vacios = {c: sum(1 for f in filas if esta_vacio(f.get(c))) for c in columnas}
    tipos = {c: sorted({type(f[c]).__name__ for f in filas if c in f}) for c in columnas}
    return {"registros": len(filas), "columnas": columnas,
            "vacios_por_columna": vacios, "tipos_por_columna": tipos}


def validar_esquema(filas, requeridas):
    """Falla si falta una columna necesaria en todo el archivo.

    Si la columna falta solo en algunos registros (posible en JSON), esos
    registros se rechazan después, en la limpieza, con su motivo.
    """
    if not filas:
        raise ValueError("No hay registros para validar")
    presentes = set()
    for fila in filas:
        presentes.update(fila.keys())
    faltantes = set(requeridas) - presentes
    if faltantes:
        raise ValueError(f"Faltan columnas: {', '.join(sorted(faltantes))}")


# --- Limpieza del histórico ------------------------------------------------
def limpiar_historico(filas):
    """Separa tandas válidas de rechazadas, con el motivo de cada rechazo.

    Decisiones de limpieza:
    - Un registro que no pasa las validaciones de TandaHistorica se rechaza.
    - Duplicados: si se repite el id o el mismo partido (torneo, año, ronda y
      equipos), se conserva el primero y se rechazan los siguientes.
    - No se corrige ni se completa ningún valor: un dato real dudoso se
      descarta en lugar de inventarlo.
    """
    validas, rechazos = [], []
    ids, claves = set(), set()
    for numero, fila in enumerate(filas, start=1):
        try:
            tanda = TandaHistorica.desde_dict(fila)
            if tanda.id in ids:
                raise ValueError(f"id repetido: {tanda.id}")
            if tanda.clave() in claves:
                raise ValueError("partido duplicado (mismo torneo, año, ronda y equipos)")
            ids.add(tanda.id)
            claves.add(tanda.clave())
            validas.append(tanda)
        except (ValueError, TypeError) as error:
            rechazos.append({"registro": numero, "id": fila.get("id", ""),
                             "motivo": str(error)})
    return validas, rechazos


def filtrar_historico(tandas, torneo=None, desde=None, hasta=None):
    """Selecciona tandas por torneo y rango de años (ambos extremos incluidos)."""
    if desde is not None and hasta is not None and desde > hasta:
        raise ValueError(f"el rango de años es inválido: {desde} > {hasta}")
    return [t for t in tandas
            if (torneo is None or t.torneo == torneo)
            and (desde is None or t.anio >= desde)
            and (hasta is None or t.anio <= hasta)]


# --- Análisis del histórico ------------------------------------------------
def _metricas(tandas):
    """Medidas de un grupo de tandas (todo el histórico o un subgrupo)."""
    goles = sum(t.total_goles() for t in tandas)
    tiros = sum(t.total_tiros() for t in tandas)
    conv = intervalo_proporcion(goles, tiros)
    muerte = sum(t.llego_a_muerte_subita() for t in tandas)
    return {
        "tandas": len(tandas),
        "penales_pateados": tiros,
        "penales_convertidos": goles,
        "conversion": round(conv["proporcion"], 4),
        "conversion_ic95": [round(conv["ic_inferior"], 4), round(conv["ic_superior"], 4)],
        "tiros_promedio": round(tiros / len(tandas), 3),
        "prop_muerte_subita": round(muerte / len(tandas), 4),
    }


def analizar_historico(tandas):
    """Analiza las tandas reales: conversión, duración, grupos y quién empieza."""
    if not tandas:
        raise ValueError("No hay tandas válidas para analizar con esos filtros")
    general = _metricas(tandas)

    grupos = defaultdict(list)
    for t in tandas:
        grupos[("torneo", t.torneo)].append(t)
        grupos[("decada", f"{t.anio // 10 * 10}s")].append(t)
    por_grupo = [{"agrupacion": tipo, "grupo": nombre, **_metricas(lista)}
                 for (tipo, nombre), lista in sorted(grupos.items())]

    distribucion = Counter(t.total_tiros() for t in tandas)

    # Quién pateó primero solo se sabe cuando un equipo pateó uno más.
    conocidas = [t for t in tandas if t.pateo_primero() is not None]
    gana_el_primero = sum(t.pateo_primero() == "ganador" for t in conocidas)
    primero = {"tandas_con_dato": len(conocidas),
               "gana_el_que_patea_primero": gana_el_primero,
               "advertencia": "subconjunto sesgado: solo tandas que terminaron "
                              "con un penal de diferencia en cantidad de tiros"}
    if conocidas:
        primero["proporcion"] = round(gana_el_primero / len(conocidas), 4)

    return {"general": general, "por_grupo": por_grupo,
            "distribucion_tiros_totales": dict(sorted(distribucion.items())),
            "quien_patea_primero": primero}


def comparar_con_modelo(tandas, modelo, efectividad_base, repeticiones, semilla):
    """Simula tandas entre equipos homogéneos y las compara con las reales.

    Sirve para ver si el simulador produce tandas parecidas a las reales en
    las medidas que no se usaron para calibrarlo (duración y muerte súbita).
    """
    real = _metricas(tandas)
    a = equipo_homogeneo("AAA", efectividad_base)
    b = equipo_homogeneo("BBB", efectividad_base)
    simuladas, resumen = simular_enfrentamiento(modelo, a, b, repeticiones, semilla)

    def tramo(total):  # las tandas muy largas se agrupan en un solo tramo
        return str(total) if total < TIROS_TRAMO_FINAL else f"{TIROS_TRAMO_FINAL}+"

    dist_real = Counter(tramo(t.total_tiros()) for t in tandas)
    dist_sim = Counter(tramo(s["tiros_a"] + s["tiros_b"]) for s in simuladas)
    filas = [
        {"medida": "conversion", "real": real["conversion"],
         "simulado": resumen["conversion"]},
        {"medida": "tiros_promedio", "real": real["tiros_promedio"],
         "simulado": resumen["tiros_promedio"]},
        {"medida": "prop_muerte_subita", "real": real["prop_muerte_subita"],
         "simulado": resumen["prop_muerte_subita"]},
    ]
    for total in sorted(set(dist_real) | set(dist_sim), key=lambda x: int(x.rstrip("+"))):
        filas.append({"medida": f"prop_tandas_de_{total}_tiros",
                      "real": round(dist_real[total] / len(tandas), 4),
                      "simulado": round(dist_sim[total] / len(simuladas), 4)})
    for fila in filas:
        fila["diferencia"] = round(fila["simulado"] - fila["real"], 4)
    return filas


# --- Planteles para el simulador -------------------------------------------
def construir_equipos(filas, efectividad_por_defecto):
    """Arma los equipos a partir de filas planas (una por jugador).

    Valores faltantes (decisión explícita, no se reemplazan por cero):
    - efectividad vacía → se usa la efectividad calibrada con datos reales y
      el pateador queda marcado como 'efectividad_estimada'.
    - temple vacío → 0.5 (neutro).
    - factor_atajada vacío → 0 (arquero promedio).
    Una fila con valores inválidos se rechaza; un equipo incompleto (menos de
    5 pateadores o sin un único arquero) se rechaza entero.
    """
    jugadores = defaultdict(lambda: {"nombre": "", "pateadores": [], "arqueros": []})
    rechazos = []
    for numero, fila in enumerate(filas, start=1):
        codigo = str(fila.get("codigo_equipo", "")).strip()
        try:
            rol = str(fila.get("rol", "")).strip().lower()
            nombre = str(fila.get("nombre", "")).strip()
            if rol == "pateador":
                estimada = esta_vacio(fila.get("efectividad"))
                efectividad = (efectividad_por_defecto if estimada
                               else fila["efectividad"])
                temple = (TEMPLE_POR_DEFECTO if esta_vacio(fila.get("temple"))
                          else fila["temple"])
                jugador = Pateador(nombre, efectividad, temple, estimada)
                jugadores[codigo]["pateadores"].append(jugador)
            elif rol == "arquero":
                factor = (0.0 if esta_vacio(fila.get("factor_atajada"))
                          else fila["factor_atajada"])
                jugadores[codigo]["arqueros"].append(Arquero(nombre, factor))
            else:
                raise ValueError(f"rol desconocido: {rol!r} (pateador o arquero)")
            jugadores[codigo]["nombre"] = str(fila.get("equipo", "")).strip()
        except ValueError as error:
            rechazos.append({"registro": numero, "equipo": codigo,
                             "motivo": str(error)})

    equipos = {}
    for codigo, datos in jugadores.items():
        try:
            if len(datos["arqueros"]) != 1:
                raise ValueError(f"debe tener exactamente un arquero "
                                 f"(tiene {len(datos['arqueros'])})")
            equipos[codigo] = Equipo(codigo, datos["nombre"], datos["pateadores"],
                                     datos["arqueros"][0])
        except ValueError as error:
            rechazos.append({"registro": "-", "equipo": codigo,
                             "motivo": f"equipo descartado: {error}"})
    return equipos, rechazos


def elegir_pateadores(equipo, nombres=None):
    """Devuelve los 5 pateadores pedidos por nombre, o los 5 mejores."""
    if not nombres:
        return equipo.mejores()
    if len(nombres) != PENALES_REGLAMENTARIOS:
        raise ValueError(f"hay que indicar {PENALES_REGLAMENTARIOS} pateadores "
                         f"(se indicaron {len(nombres)})")
    return [equipo.pateador(n) for n in nombres]


def buscar_equipo(equipos, codigo):
    if codigo not in equipos:
        disponibles = ", ".join(sorted(equipos)) or "ninguno"
        raise ValueError(f"no hay un equipo válido con código {codigo!r} "
                         f"(disponibles: {disponibles})")
    return equipos[codigo]


def verificar_ranking(ranking):
    """Controles del resultado de recomendar_orden antes de guardarlo."""
    if len(ranking) != 120:
        raise ValueError(f"se esperaban 120 órdenes y hay {len(ranking)}")
    ordenes = {tuple(r["orden"]) for r in ranking}
    if len(ordenes) != 120:
        raise ValueError("hay órdenes repetidos en el ranking")
    for r in ranking:
        if not 0 <= r["prob_ganar"] <= 1:
            raise ValueError(f"probabilidad fuera de rango en {r['orden']}")


# --- Guardado ---------------------------------------------------------------
def guardar_csv(filas, ruta, campos=None):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    campos = campos or (list(filas[0]) if filas else ["sin_datos"])
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


def guardar_json(contenido, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, indent=2, ensure_ascii=False)
    return ruta
