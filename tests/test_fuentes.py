import json
import tempfile
import unittest
from pathlib import Path

from src.fuentes import FuenteCSV, FuenteJSON, elegir_fuente
from src.modelos import TandaHistorica
from tests.utilidades import DATA


class TestFuentes(unittest.TestCase):
    def test_csv_carga_todas_las_tandas(self):
        datos = FuenteCSV().cargar(DATA / "tandas_historicas.csv")
        self.assertEqual(len(datos), 97)
        self.assertEqual(datos[0]["id"], "MUN-1982-01")

    def test_csv_y_json_son_equivalentes(self):
        """Propiedad: las dos lecturas producen las mismas tandas."""
        desde_csv = [TandaHistorica.desde_dict(f).a_dict()
                     for f in FuenteCSV().cargar(DATA / "tandas_historicas.csv")]
        desde_json = [TandaHistorica.desde_dict(f).a_dict()
                      for f in FuenteJSON().cargar(DATA / "tandas_historicas.json")]
        self.assertEqual(desde_csv, desde_json)

    def test_archivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            FuenteCSV().cargar(DATA / "no_existe.csv")

    def test_formato_no_soportado(self):
        with self.assertRaises(ValueError):
            elegir_fuente("datos.txt")

    def _archivo(self, contenido, extension):
        carpeta = tempfile.mkdtemp()
        ruta = Path(carpeta) / f"prueba{extension}"
        ruta.write_text(contenido, encoding="utf-8")
        return ruta

    def test_csv_solo_con_encabezado_da_error(self):
        with self.assertRaises(ValueError):
            FuenteCSV().cargar(self._archivo("id,torneo\n", ".csv"))

    def test_json_mal_formado(self):
        with self.assertRaises(ValueError):
            FuenteJSON().cargar(self._archivo("[{\"id\": ", ".json"))

    def test_json_que_no_es_lista(self):
        with self.assertRaises(ValueError):
            FuenteJSON().cargar(self._archivo(json.dumps({"id": 1}), ".json"))

    def test_json_con_elemento_que_no_es_objeto(self):
        with self.assertRaises(ValueError):
            FuenteJSON().cargar(self._archivo(json.dumps([{"id": 1}, 5]), ".json"))


if __name__ == "__main__":
    unittest.main()
