"""Fuentes de datos: lectura de escenarios desde CSV o JSON."""

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path


class FuenteDatos(ABC):
    """Contrato común: toda fuente sabe cargar una lista de diccionarios."""

    @abstractmethod
    def cargar(self, ruta):
        """Lee el archivo y devuelve una lista de diccionarios."""


class FuenteCSV(FuenteDatos):
    def cargar(self, ruta):
        try:
            with open(ruta, newline="", encoding="utf-8") as archivo:
                return list(csv.DictReader(archivo))
        except FileNotFoundError:
            raise FileNotFoundError(f"No se encontro el archivo: {ruta}")


class FuenteJSON(FuenteDatos):
    def cargar(self, ruta):
        try:
            with open(ruta, encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except FileNotFoundError:
            raise FileNotFoundError(f"No se encontro el archivo: {ruta}")
        except json.JSONDecodeError as error:
            raise ValueError(f"El JSON esta mal formado: {error}")

        if not isinstance(datos, list):
            raise ValueError("El JSON debe ser una lista de objetos.")
        return datos


def elegir_fuente(ruta):
    """Devuelve la fuente adecuada segun la extension del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise ValueError(f"Formato no soportado: '{extension}'. Usar .csv o .json")