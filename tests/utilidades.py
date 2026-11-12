"""Datos de prueba compartidos por los tests."""

from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def fila_tanda(**cambios):
    """Una tanda válida (final del Mundial 2022) como la leería el CSV."""
    fila = {"id": "MUN-2022-05", "torneo": "Mundial", "anio": "2022",
            "ronda": "F", "ganador": "Argentina", "perdedor": "France",
            "resultado_partido": "3-3", "goles_ganador": "4",
            "goles_perdedor": "2", "tiros_ganador": "4", "tiros_perdedor": "4"}
    fila.update(cambios)
    return fila
