import unittest
from pathlib import Path

from src.fuentes import FuenteCSV, FuenteJSON, elegir_fuente

DATA = Path(__file__).resolve().parent.parent / "data"


class TestFuentes(unittest.TestCase):
    def test_csv_carga_cuatro_escenarios(self):
        datos = FuenteCSV().cargar(DATA / "escenarios.csv")
        self.assertEqual(len(datos), 4)
        self.assertEqual(datos[0]["id"], "ESC-001")

    def test_csv_y_json_tienen_mismos_ids(self):
        csv_datos = FuenteCSV().cargar(DATA / "escenarios.csv")
        json_datos = FuenteJSON().cargar(DATA / "escenarios.json")
        self.assertEqual([d["id"] for d in csv_datos],
                         [d["id"] for d in json_datos])

    def test_archivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            FuenteCSV().cargar(DATA / "no_existe.csv")

    def test_formato_no_soportado(self):
        with self.assertRaises(ValueError):
            elegir_fuente("datos.txt")


if __name__ == "__main__":
    unittest.main()