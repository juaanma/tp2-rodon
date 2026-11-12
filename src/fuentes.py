"""Fuentes de datos: lectura de archivos CSV o JSON con una interfaz común.

Las dos fuentes devuelven la misma representación (una lista de diccionarios),
así el resto del programa no depende del formato del archivo de origen.
"""

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path


class FuenteDatos(ABC):
    """Contrato común: toda fuente sabe cargar una lista de diccionarios."""

    def cargar(self, ruta):
        """Lee el archivo y devuelve una lista de diccionarios.

        Controla los errores comunes a todos los formatos (archivo inexistente,
        archivo vacío) y delega la lectura concreta en `_leer`.
        """
        ruta = Path(ruta)
        if not ruta.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {ruta}")
        try:
            filas = self._leer(ruta)
        except UnicodeDecodeError:
            raise ValueError(f"El archivo {ruta} no está codificado en UTF-8")
        if not filas:
            raise ValueError(f"El archivo {ruta} no contiene registros")
        return filas

    @abstractmethod
    def _leer(self, ruta):
        """Lectura específica de cada formato."""


class FuenteCSV(FuenteDatos):
    """Lee un CSV con encabezado. Todos los valores llegan como texto."""

    def _leer(self, ruta):
        with open(ruta, newline="", encoding="utf-8") as archivo:
            return list(csv.DictReader(archivo))


class FuenteJSON(FuenteDatos):
    """Lee un JSON que debe ser una lista de objetos (uno por registro)."""

    def _leer(self, ruta):
        with open(ruta, encoding="utf-8") as archivo:
            try:
                datos = json.load(archivo)
            except json.JSONDecodeError as error:
                raise ValueError(f"El JSON {ruta} está mal formado: {error}")
        if not isinstance(datos, list):
            raise ValueError("El JSON debe ser una lista de objetos.")
        for posicion, registro in enumerate(datos, start=1):
            if not isinstance(registro, dict):
                raise ValueError(
                    f"El elemento {posicion} del JSON no es un objeto con campos")
        return datos


def elegir_fuente(ruta):
    """Devuelve la fuente adecuada según la extensión del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise ValueError(f"Formato no soportado: '{extension}'. Usar .csv o .json")
