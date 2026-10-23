"""Modelo del dominio: un escenario de simulacion de tandas de penales."""

import re

# Regex: "ESC-" seguido de exactamente 3 digitos (ej: ESC-001).
# No valida que el escenario exista, solo que el texto tenga ese formato.
PATRON_ID = re.compile(r"ESC-\d{3}")


def _a_numero(valor, nombre):
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"'{nombre}' debe ser un numero (recibido: {valor!r})")


def _a_entero(valor, nombre):
    numero = _a_numero(valor, nombre)
    if not numero.is_integer():
        raise ValueError(f"'{nombre}' debe ser un entero (recibido: {valor!r})")
    return int(numero)


class Escenario:
    """Parametros de una simulacion, ya validados."""

    def __init__(self, id, prob_gol_a, prob_gol_b, repeticiones, semilla):
        if not PATRON_ID.fullmatch(str(id)):
            raise ValueError(f"id invalido: {id!r} (formato esperado: ESC-001)")
        for nombre, prob in (("prob_gol_a", prob_gol_a),
                             ("prob_gol_b", prob_gol_b)):
            if not 0 <= prob <= 1:
                raise ValueError(f"'{nombre}' debe estar entre 0 y 1 (recibido: {prob})")
        if repeticiones <= 0:
            raise ValueError(f"'repeticiones' debe ser mayor que 0 (recibido: {repeticiones})")

        self.id = id
        self.prob_gol_a = prob_gol_a
        self.prob_gol_b = prob_gol_b
        self.repeticiones = repeticiones
        self.semilla = semilla

    @classmethod
    def desde_dict(cls, fila):
        """Crea un Escenario desde un diccionario (de CSV o de JSON)."""
        try:
            return cls(
                id=str(fila["id"]).strip(),
                prob_gol_a=_a_numero(fila["prob_gol_a"], "prob_gol_a"),
                prob_gol_b=_a_numero(fila["prob_gol_b"], "prob_gol_b"),
                repeticiones=_a_entero(fila["repeticiones"], "repeticiones"),
                semilla=_a_entero(fila["semilla"], "semilla"),
            )
        except KeyError as error:
            raise ValueError(f"Falta la columna {error} en el escenario")

    def a_dict(self):
        return {
            "id": self.id,
            "prob_gol_a": self.prob_gol_a,
            "prob_gol_b": self.prob_gol_b,
            "repeticiones": self.repeticiones,
            "semilla": self.semilla,
        }