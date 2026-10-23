"""Simulacion de tandas de penales, resumen y guardado de resultados."""

import csv
import json
import random
from pathlib import Path

PENALES_BASE = 5  # penales por equipo antes de la muerte subita

CAMPOS_TANDA = ["id_escenario", "nro_tanda", "goles_a", "goles_b",
                "penales_pateados", "ganador"]


def _patear(rng, probabilidad):
    """True si el penal se convierte. Con prob 1 siempre, con prob 0 nunca."""
    return rng.random() < probabilidad


def simular_tanda(rng, escenario, nro_tanda):
    """Simula una tanda: 5 penales por equipo y muerte subita si hay empate."""
    goles_a = 0
    goles_b = 0
    for _ in range(PENALES_BASE):
        goles_a += _patear(rng, escenario.prob_gol_a)
        goles_b += _patear(rng, escenario.prob_gol_b)
    penales = PENALES_BASE

    while goles_a == goles_b:  # muerte subita: de a un penal por equipo
        goles_a += _patear(rng, escenario.prob_gol_a)
        goles_b += _patear(rng, escenario.prob_gol_b)
        penales += 1

    return {
        "id_escenario": escenario.id,
        "nro_tanda": nro_tanda,
        "goles_a": goles_a,
        "goles_b": goles_b,
        "penales_pateados": penales,
        "ganador": "A" if goles_a > goles_b else "B",
    }


def ejecutar_escenario(escenario):
    """Simula todas las repeticiones de un escenario con su semilla."""
    rng = random.Random(escenario.semilla)  # un generador por escenario
    return [simular_tanda(rng, escenario, i)
            for i in range(1, escenario.repeticiones + 1)]


def resumir_experimento(tandas):
    """Calcula victorias, porcentajes y promedio de penales por equipo."""
    total = len(tandas)
    if total == 0:
        raise ValueError("No hay tandas para resumir")
    victorias_a = sum(1 for t in tandas if t["ganador"] == "A")
    victorias_b = total - victorias_a
    return {
        "tandas": total,
        "victorias_a": victorias_a,
        "victorias_b": victorias_b,
        "porcentaje_a": round(100 * victorias_a / total, 2),
        "porcentaje_b": round(100 * victorias_b / total, 2),
        "promedio_penales": round(
            sum(t["penales_pateados"] for t in tandas) / total, 2),
    }


def guardar_experimento(escenario, tandas, carpeta="outputs"):
    """Guarda las tandas (CSV) y la configuracion con el resumen (JSON).

    El id va en el nombre del archivo para que un escenario no pise a otro.
    """
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    ruta_tandas = carpeta / f"{escenario.id}_tandas.csv"
    with open(ruta_tandas, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS_TANDA)
        escritor.writeheader()
        escritor.writerows(tandas)

    ruta_resumen = carpeta / f"{escenario.id}_resumen.json"
    contenido = {"escenario": escenario.a_dict(),
                 "resultado": resumir_experimento(tandas)}
    with open(ruta_resumen, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, indent=2, ensure_ascii=False)

    return ruta_tandas, ruta_resumen