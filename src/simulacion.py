"""Simulador de tandas penal por penal, con pateadores, arquero y presión.

Responde la pregunta central del programa: dado un plantel, ¿qué
probabilidad tiene de ganar la tanda y en qué orden conviene patear?
"""

import itertools
import math
import random

from src.modelos import (PENALES_REGLAMENTARIOS, Arquero, Equipo, Pateador,
                         tanda_decidida)

Z_95 = 1.96  # para intervalos de confianza del 95 %


def intervalo_proporcion(exitos, total):
    """Proporción con su intervalo de confianza del 95 % (aprox. normal)."""
    if total <= 0:
        raise ValueError("no se puede estimar una proporción sin observaciones")
    p = exitos / total
    margen = Z_95 * math.sqrt(p * (1 - p) / total)
    return {"proporcion": p,
            "ic_inferior": max(0.0, p - margen),
            "ic_superior": min(1.0, p + margen)}


class ModeloPenales:
    """Reglas para calcular la probabilidad de cada penal.

    presion: caída relativa máxima de la efectividad en un penal en que errar
    significa perder (para un pateador de temple 0). Es un supuesto del
    modelo, no sale de los datos: con presion=0 la presión no influye.
    """

    def __init__(self, presion=0.25):
        if not 0 <= presion < 1:
            raise ValueError(f"'presion' debe estar en [0, 1) (recibido: {presion})")
        self.presion = presion

    def probabilidad_gol(self, pateador, arquero_rival, bajo_presion):
        base = (pateador.efectividad_bajo_presion(self.presion)
                if bajo_presion else pateador.efectividad)
        return arquero_rival.ajustar(base)

    def simular_tanda(self, equipo_1, orden_1, equipo_2, orden_2, rng):
        """Simula una tanda en que el equipo 1 patea primero.

        Devuelve el marcador, los tiros, el ganador (1 o 2) y cuántos penales
        se patearon bajo presión.
        """
        goles = [0, 0]
        tiros = [0, 0]
        bajo_presion = 0
        equipos = (equipo_1, equipo_2)
        ordenes = (orden_1, orden_2)
        while not tanda_decidida(goles[0], tiros[0], goles[1], tiros[1]):
            lado = 0 if tiros[0] == tiros[1] else 1
            pateador = ordenes[lado][tiros[lado] % len(ordenes[lado])]
            rival = equipos[1 - lado]
            # ¿Si erra este penal, pierde? (errar nunca puede hacerlo ganar)
            tiros_si_erra = list(tiros)
            tiros_si_erra[lado] += 1
            presionado = tanda_decidida(goles[0], tiros_si_erra[0],
                                        goles[1], tiros_si_erra[1])
            bajo_presion += presionado
            p = self.probabilidad_gol(pateador, rival.arquero, presionado)
            goles[lado] += rng.random() < p
            tiros[lado] += 1
        return {"goles_1": goles[0], "goles_2": goles[1],
                "tiros_1": tiros[0], "tiros_2": tiros[1],
                "ganador": 1 if goles[0] > goles[1] else 2,
                "penales_bajo_presion": bajo_presion}

    def jugar(self, equipo_a, orden_a, equipo_b, orden_b, rng, empieza):
        """Juega una tanda A vs B. `empieza` es 'A', 'B' o 'sorteo'.

        Devuelve el resultado expresado desde el punto de vista de A.
        """
        if empieza == "sorteo":
            a_primero = rng.random() < 0.5
        elif empieza in ("A", "B"):
            a_primero = empieza == "A"
        else:
            raise ValueError(f"'empieza' debe ser A, B o sorteo (recibido: {empieza})")
        if a_primero:
            r = self.simular_tanda(equipo_a, orden_a, equipo_b, orden_b, rng)
            goles_a, goles_b, tiros_a, tiros_b = (r["goles_1"], r["goles_2"],
                                                  r["tiros_1"], r["tiros_2"])
        else:
            r = self.simular_tanda(equipo_b, orden_b, equipo_a, orden_a, rng)
            goles_a, goles_b, tiros_a, tiros_b = (r["goles_2"], r["goles_1"],
                                                  r["tiros_2"], r["tiros_1"])
        return {"a_pateo_primero": a_primero, "goles_a": goles_a, "goles_b": goles_b,
                "tiros_a": tiros_a, "tiros_b": tiros_b,
                "gana_a": goles_a > goles_b,
                "penales_bajo_presion": r["penales_bajo_presion"]}


def simular_enfrentamiento(modelo, equipo_a, equipo_b, repeticiones, semilla,
                           orden_a=None, orden_b=None, empieza="sorteo"):
    """Repite la tanda A vs B y devuelve las tandas y un resumen.

    Si no se indica un orden, cada equipo patea con sus 5 mejores por
    efectividad. Con la misma semilla se obtienen exactamente los mismos
    resultados.
    """
    if repeticiones <= 0:
        raise ValueError("'repeticiones' debe ser mayor que 0")
    orden_a = equipo_a.orden_completo(orden_a or equipo_a.mejores())
    orden_b = equipo_b.orden_completo(orden_b or equipo_b.mejores())
    rng = random.Random(semilla)
    tandas = [modelo.jugar(equipo_a, orden_a, equipo_b, orden_b, rng, empieza)
              for _ in range(repeticiones)]
    return tandas, resumir_simulacion(tandas)


def resumir_simulacion(tandas):
    """Resume tandas simuladas: probabilidad de que gane A y otras medidas."""
    total = len(tandas)
    if total == 0:
        raise ValueError("no hay tandas para resumir")
    victorias_a = sum(t["gana_a"] for t in tandas)
    ic = intervalo_proporcion(victorias_a, total)
    goles = sum(t["goles_a"] + t["goles_b"] for t in tandas)
    tiros = sum(t["tiros_a"] + t["tiros_b"] for t in tandas)
    muerte_subita = sum(max(t["tiros_a"], t["tiros_b"]) > PENALES_REGLAMENTARIOS
                        for t in tandas)
    return {
        "tandas": total,
        "victorias_a": victorias_a,
        "victorias_b": total - victorias_a,
        "prob_gana_a": round(ic["proporcion"], 4),
        "ic95_gana_a": [round(ic["ic_inferior"], 4), round(ic["ic_superior"], 4)],
        "conversion": round(goles / tiros, 4),
        "tiros_promedio": round(tiros / total, 3),
        "prop_muerte_subita": round(muerte_subita / total, 4),
    }


def recomendar_orden(modelo, equipo, rival, candidatos, repeticiones, semilla,
                     empieza="sorteo"):
    """Prueba todos los órdenes posibles de los 5 pateadores elegidos.

    Todas las permutaciones usan la misma semilla (números aleatorios
    comunes): así la diferencia entre dos órdenes se debe al orden y no a la
    suerte de la simulación. El rival patea con sus 5 mejores.

    Devuelve una lista de diccionarios ordenada de mejor a peor.
    """
    if len(candidatos) != PENALES_REGLAMENTARIOS:
        raise ValueError(f"hay que elegir exactamente {PENALES_REGLAMENTARIOS} "
                         f"pateadores (recibidos: {len(candidatos)})")
    if len({p.nombre for p in candidatos}) != len(candidatos):
        raise ValueError("hay pateadores repetidos entre los elegidos")
    ranking = []
    for permutacion in itertools.permutations(candidatos):
        tandas, resumen = simular_enfrentamiento(
            modelo, equipo, rival, repeticiones, semilla,
            orden_a=list(permutacion), empieza=empieza)
        ranking.append({"orden": [p.nombre for p in permutacion],
                        "prob_ganar": resumen["prob_gana_a"],
                        "ic95": resumen["ic95_gana_a"],
                        "resultados": [t["gana_a"] for t in tandas]})
    ranking.sort(key=lambda r: (-r["prob_ganar"], r["orden"]))
    for posicion, fila in enumerate(ranking, start=1):
        fila["posicion"] = posicion
    return ranking


def diferencia_pareada(resultados_x, resultados_y):
    """Diferencia de probabilidad de ganar entre dos órdenes simulados con la
    misma semilla, con IC 95 % calculado sobre las diferencias tanda a tanda.

    Como las dos simulaciones comparten los números aleatorios, comparar
    tanda por tanda elimina gran parte del ruido de la simulación.
    """
    if len(resultados_x) != len(resultados_y) or not resultados_x:
        raise ValueError("las simulaciones a comparar deben tener el mismo tamaño")
    n = len(resultados_x)
    difs = [int(x) - int(y) for x, y in zip(resultados_x, resultados_y)]
    media = sum(difs) / n
    varianza = sum((d - media) ** 2 for d in difs) / (n - 1) if n > 1 else 0.0
    margen = Z_95 * math.sqrt(varianza / n)
    return {"diferencia": round(media, 4),
            "ic95": [round(media - margen, 4), round(media + margen, 4)]}


def equipo_homogeneo(codigo, probabilidad, temple=0.5, cantidad=11):
    """Equipo en que todos convierten con la misma probabilidad y el arquero
    es promedio. Se usa para comparar el modelo con los datos reales."""
    pateadores = [Pateador(f"{codigo}{i}", probabilidad, temple=temple)
                  for i in range(1, cantidad + 1)]
    return Equipo(codigo, f"Homogéneo {codigo}", pateadores, Arquero("promedio", 0))


def calibrar_efectividad(modelo, conversion_objetivo, repeticiones=4000,
                         semilla=2026, temple=0.5, iteraciones=18):
    """Busca la efectividad base que reproduce la conversión real.

    Con presión, la conversión simulada queda por debajo de la efectividad
    base (algunos penales se patean presionados). Por bisección se busca la
    efectividad que hace que la conversión simulada iguale a la observada.
    """
    if not 0 < conversion_objetivo < 1:
        raise ValueError("la conversión objetivo debe estar entre 0 y 1")
    bajo, alto = conversion_objetivo, 0.99
    for _ in range(iteraciones):
        medio = (bajo + alto) / 2
        a = equipo_homogeneo("AAA", medio, temple)
        b = equipo_homogeneo("BBB", medio, temple)
        _, resumen = simular_enfrentamiento(modelo, a, b, repeticiones, semilla)
        if resumen["conversion"] < conversion_objetivo:
            bajo = medio
        else:
            alto = medio
    return round((bajo + alto) / 2, 4)
