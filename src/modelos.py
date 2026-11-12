"""Modelo del dominio: tandas de penales reales, pateadores, arqueros y equipos.

Las reglas de la tanda (cuándo termina) están en `tanda_decidida`, y la usan
tanto la validación de los datos históricos como el simulador. Así una tanda
simulada y una real se juzgan con la misma regla.
"""

import re
from collections import deque
from datetime import date

PENALES_REGLAMENTARIOS = 5   # penales por equipo antes de la muerte súbita
ANIO_PRIMERA_TANDA = 1976    # primera tanda en un torneo de los datos (Euro 1976)

# --- Expresiones regulares -------------------------------------------------
# id de tanda: torneo (3 letras) - año - número de orden dentro del año.
#   MUN = Mundial, EUR = Eurocopa, CAM = Copa América. Ej: MUN-2022-05
PATRON_ID_TANDA = re.compile(r"(MUN|EUR|CAM)-(\d{4})-(\d{2})")
# resultado del partido antes de los penales, ej: "1-1" o "3-3".
PATRON_RESULTADO = re.compile(r"(\d{1,2})-(\d{1,2})")
# ronda: F (final), SF (semi), QF (cuartos), 3/4 (tercer puesto),
#        1R/2R/3R (rondas de eliminación previas, según el torneo).
PATRON_RONDA = re.compile(r"F|SF|QF|3/4|[1-3]R")
# código de equipo en los planteles: tres letras mayúsculas, ej: NOR
PATRON_CODIGO_EQUIPO = re.compile(r"[A-Z]{3}")

TORNEOS = {"MUN": "Mundial", "EUR": "Eurocopa", "CAM": "Copa America"}


# --- Reglas de la tanda ----------------------------------------------------
def tanda_decidida(goles_1, tiros_1, goles_2, tiros_2,
                   n=PENALES_REGLAMENTARIOS):
    """Indica si la tanda ya terminó. El equipo 1 es el que patea primero.

    - En los 5 penales reglamentarios termina cuando un equipo ya no puede
      alcanzar al otro aunque convierta todos los que le quedan.
    - En muerte súbita termina al completar una ronda con distinto resultado.
    """
    if tiros_1 <= n and tiros_2 <= n:
        quedan_1 = n - tiros_1
        quedan_2 = n - tiros_2
        return goles_1 + quedan_1 < goles_2 or goles_2 + quedan_2 < goles_1
    return tiros_1 == tiros_2 and goles_1 != goles_2


def _alcanzable(goles_1, tiros_1, goles_2, tiros_2):
    """Busca si se llega a ese marcador final pateando alternadamente.

    Recorre todos los estados posibles (tiros y goles de cada equipo) desde
    0-0 y no sigue avanzando por los estados en que la tanda ya terminó.
    """
    objetivo = (goles_1, tiros_1, goles_2, tiros_2)
    inicio = (0, 0, 0, 0)
    pendientes = deque([inicio])
    vistos = {inicio}
    while pendientes:
        estado = pendientes.popleft()
        g1, t1, g2, t2 = estado
        if tanda_decidida(g1, t1, g2, t2):
            if estado == objetivo:
                return True
            continue
        patea_el_1 = t1 == t2
        for convierte in (0, 1):
            if patea_el_1:
                siguiente = (g1 + convierte, t1 + 1, g2, t2)
            else:
                siguiente = (g1, t1, g2 + convierte, t2 + 1)
            if (siguiente[1] <= tiros_1 and siguiente[3] <= tiros_2
                    and siguiente not in vistos):
                vistos.add(siguiente)
                pendientes.append(siguiente)
    return False


def resultado_posible(goles_ganador, tiros_ganador, goles_perdedor, tiros_perdedor):
    """True si el marcador puede darse con el reglamento, pateando primero
    cualquiera de los dos equipos (los datos no siempre dicen quién empezó)."""
    return (_alcanzable(goles_ganador, tiros_ganador, goles_perdedor, tiros_perdedor)
            or _alcanzable(goles_perdedor, tiros_perdedor, goles_ganador, tiros_ganador))


# --- Conversión de valores -------------------------------------------------
def a_entero(valor, nombre):
    """Convierte texto o número a entero, con un mensaje claro si no se puede."""
    if valor is None or str(valor).strip() == "":
        raise ValueError(f"'{nombre}' está vacío")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"'{nombre}' debe ser un número (recibido: {valor!r})")
    if not numero.is_integer():
        raise ValueError(f"'{nombre}' debe ser un entero (recibido: {valor!r})")
    return int(numero)


def a_probabilidad(valor, nombre, minimo=0.0, maximo=1.0):
    """Convierte a float y controla que esté en [minimo, maximo]."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"'{nombre}' debe ser un número (recibido: {valor!r})")
    if not minimo <= numero <= maximo:  # también descarta NaN
        raise ValueError(
            f"'{nombre}' debe estar entre {minimo} y {maximo} (recibido: {valor})")
    return numero


def esta_vacio(valor):
    return valor is None or str(valor).strip() == ""


# --- Tanda histórica -------------------------------------------------------
class TandaHistorica:
    """Una tanda de penales real de un Mundial, Eurocopa o Copa América."""

    CAMPOS = ["id", "torneo", "anio", "ronda", "ganador", "perdedor",
              "resultado_partido", "goles_ganador", "goles_perdedor",
              "tiros_ganador", "tiros_perdedor"]

    def __init__(self, id, torneo, anio, ronda, ganador, perdedor,
                 resultado_partido, goles_ganador, goles_perdedor,
                 tiros_ganador, tiros_perdedor):
        coincidencia = PATRON_ID_TANDA.fullmatch(id)
        if not coincidencia:
            raise ValueError(f"id inválido: {id!r} (formato esperado: MUN-2022-01)")
        prefijo, anio_id, _ = coincidencia.groups()
        if TORNEOS[prefijo] != torneo:
            raise ValueError(f"el id {id} no corresponde al torneo {torneo!r}")
        if int(anio_id) != anio:
            raise ValueError(f"el año del id ({anio_id}) no coincide con anio={anio}")
        if not ANIO_PRIMERA_TANDA <= anio <= date.today().year:
            raise ValueError(f"anio fuera de rango: {anio}")
        if not PATRON_RONDA.fullmatch(ronda):
            raise ValueError(f"ronda desconocida: {ronda!r}")
        if not ganador or not perdedor or ganador == perdedor:
            raise ValueError("ganador y perdedor deben ser dos equipos distintos")

        partido = PATRON_RESULTADO.fullmatch(resultado_partido)
        if not partido:
            raise ValueError(f"resultado del partido inválido: {resultado_partido!r}")
        if partido.group(1) != partido.group(2):
            raise ValueError(
                f"el partido terminó {resultado_partido}: sin empate no hay penales")

        for nombre, goles, tiros in (("ganador", goles_ganador, tiros_ganador),
                                     ("perdedor", goles_perdedor, tiros_perdedor)):
            if tiros < 1 or goles < 0:
                raise ValueError(f"tiros/goles negativos o nulos del {nombre}")
            if goles > tiros:
                raise ValueError(f"el {nombre} no puede convertir más penales "
                                 f"({goles}) que los que pateó ({tiros})")
        if goles_ganador <= goles_perdedor:
            raise ValueError("el ganador debe convertir más penales que el perdedor")
        if not resultado_posible(goles_ganador, tiros_ganador,
                                 goles_perdedor, tiros_perdedor):
            raise ValueError(
                f"marcador imposible según el reglamento: {goles_ganador}-"
                f"{goles_perdedor} con {tiros_ganador} y {tiros_perdedor} tiros")

        self.id = id
        self.torneo = torneo
        self.anio = anio
        self.ronda = ronda
        self.ganador = ganador
        self.perdedor = perdedor
        self.resultado_partido = resultado_partido
        self.goles_ganador = goles_ganador
        self.goles_perdedor = goles_perdedor
        self.tiros_ganador = tiros_ganador
        self.tiros_perdedor = tiros_perdedor

    @classmethod
    def desde_dict(cls, fila):
        """Crea la tanda desde un diccionario leído de CSV (texto) o JSON."""
        faltantes = [c for c in cls.CAMPOS if c not in fila]
        if faltantes:
            raise ValueError(f"faltan campos: {', '.join(faltantes)}")
        textos = {c: str(fila[c]).strip() for c in
                  ("id", "torneo", "ronda", "ganador", "perdedor", "resultado_partido")}
        vacios = [c for c, v in textos.items() if v == ""]
        if vacios:
            raise ValueError(f"campos vacíos: {', '.join(vacios)}")
        return cls(
            anio=a_entero(fila["anio"], "anio"),
            goles_ganador=a_entero(fila["goles_ganador"], "goles_ganador"),
            goles_perdedor=a_entero(fila["goles_perdedor"], "goles_perdedor"),
            tiros_ganador=a_entero(fila["tiros_ganador"], "tiros_ganador"),
            tiros_perdedor=a_entero(fila["tiros_perdedor"], "tiros_perdedor"),
            **textos,
        )

    def clave(self):
        """Identifica el partido sin depender del id (para detectar duplicados)."""
        equipos = tuple(sorted((self.ganador, self.perdedor)))
        return (self.torneo, self.anio, self.ronda, equipos)

    def total_tiros(self):
        return self.tiros_ganador + self.tiros_perdedor

    def total_goles(self):
        return self.goles_ganador + self.goles_perdedor

    def conversion(self):
        """Proporción de penales convertidos en esta tanda."""
        return self.total_goles() / self.total_tiros()

    def llego_a_muerte_subita(self):
        return max(self.tiros_ganador, self.tiros_perdedor) > PENALES_REGLAMENTARIOS

    def pateo_primero(self):
        """'ganador', 'perdedor' o None si con estos datos no se puede saber.

        Si un equipo pateó un penal más que el otro, ese equipo empezó.
        """
        if self.tiros_ganador > self.tiros_perdedor:
            return "ganador"
        if self.tiros_perdedor > self.tiros_ganador:
            return "perdedor"
        return None

    def a_dict(self):
        return {c: getattr(self, c) for c in self.CAMPOS}


# --- Jugadores y equipos (para el simulador) -------------------------------
class Pateador:
    """Un pateador con su efectividad y su 'temple' ante la presión.

    efectividad: probabilidad de convertir contra un arquero promedio.
    temple: 0 = rinde mucho peor bajo presión, 1 = la presión no lo afecta.
    """

    def __init__(self, nombre, efectividad, temple=0.5, efectividad_estimada=False):
        if not nombre:
            raise ValueError("el pateador necesita un nombre")
        self.nombre = nombre
        self.efectividad = a_probabilidad(efectividad, f"efectividad de {nombre}")
        self.temple = a_probabilidad(temple, f"temple de {nombre}")
        # True si la efectividad no venía en los datos y se usó el promedio real
        self.efectividad_estimada = efectividad_estimada

    def efectividad_bajo_presion(self, presion):
        """Efectividad en un penal en que errar significa perder la tanda.

        `presion` es la caída máxima (para temple 0); con temple 1 no cae.
        """
        return self.efectividad * (1 - presion * (1 - self.temple))

    def __repr__(self):
        return f"Pateador({self.nombre!r}, {self.efectividad}, temple={self.temple})"


class Arquero:
    """Arquero con un ajuste respecto de un arquero promedio.

    factor_atajada: puntos de probabilidad que le resta al pateador.
    0.05 => el pateador convierte 5 puntos menos que contra uno promedio.
    """

    LIMITE = 0.3

    def __init__(self, nombre, factor_atajada=0.0):
        if not nombre:
            raise ValueError("el arquero necesita un nombre")
        self.nombre = nombre
        self.factor_atajada = a_probabilidad(
            factor_atajada, f"factor_atajada de {nombre}", -self.LIMITE, self.LIMITE)

    def ajustar(self, probabilidad):
        """Probabilidad de gol contra este arquero, acotada a [0.01, 0.99].

        Se acota porque ningún penal es imposible ni seguro.
        """
        return min(0.99, max(0.01, probabilidad - self.factor_atajada))


class Equipo:
    """Plantel disponible para una tanda: pateadores y un arquero."""

    def __init__(self, codigo, nombre, pateadores, arquero):
        if not PATRON_CODIGO_EQUIPO.fullmatch(codigo):
            raise ValueError(f"código de equipo inválido: {codigo!r} (ej: NOR)")
        if len(pateadores) < PENALES_REGLAMENTARIOS:
            raise ValueError(f"{codigo} tiene {len(pateadores)} pateadores; "
                             f"se necesitan al menos {PENALES_REGLAMENTARIOS}")
        nombres = [p.nombre for p in pateadores]
        if len(set(nombres)) != len(nombres):
            raise ValueError(f"{codigo} tiene pateadores con nombre repetido")
        if arquero is None:
            raise ValueError(f"{codigo} no tiene arquero")
        self.codigo = codigo
        self.nombre = nombre
        self.pateadores = list(pateadores)
        self.arquero = arquero

    def pateador(self, nombre):
        for p in self.pateadores:
            if p.nombre == nombre:
                return p
        raise ValueError(f"{self.codigo} no tiene un pateador llamado {nombre!r}")

    def mejores(self, cantidad=PENALES_REGLAMENTARIOS):
        """Los pateadores de mayor efectividad (desempate por nombre)."""
        ordenados = sorted(self.pateadores, key=lambda p: (-p.efectividad, p.nombre))
        return ordenados[:cantidad]

    def orden_completo(self, primeros):
        """Orden para toda la tanda: los elegidos y después el resto del plantel
        (para la muerte súbita), en el orden en que figura en los datos."""
        elegidos = {p.nombre for p in primeros}
        return list(primeros) + [p for p in self.pateadores if p.nombre not in elegidos]
