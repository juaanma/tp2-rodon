import unittest
from pathlib import Path

from src.fuentes import FuenteCSV, FuenteJSON
from src.modelos import Escenario

DATA = Path(__file__).resolve().parent.parent / "data"


class TestEscenario(unittest.TestCase):
    def test_escenario_valido_desde_texto(self):
        fila = {"id": "ESC-001", "prob_gol_a": "0.75", "prob_gol_b": "0.70",
                "repeticiones": "1000", "semilla": "42"}
        esc = Escenario.desde_dict(fila)
        self.assertEqual(esc.prob_gol_a, 0.75)
        self.assertEqual(esc.repeticiones, 1000)

    def test_id_con_formato_invalido(self):
        fila = {"id": "ESC-1", "prob_gol_a": 0.5, "prob_gol_b": 0.5,
                "repeticiones": 10, "semilla": 1}
        with self.assertRaises(ValueError):
            Escenario.desde_dict(fila)

    def test_probabilidad_fuera_de_rango(self):
        fila = {"id": "ESC-001", "prob_gol_a": 1.5, "prob_gol_b": 0.5,
                "repeticiones": 10, "semilla": 1}
        with self.assertRaises(ValueError):
            Escenario.desde_dict(fila)

    def test_repeticiones_no_positivas(self):
        fila = {"id": "ESC-001", "prob_gol_a": 0.5, "prob_gol_b": 0.5,
                "repeticiones": 0, "semilla": 1}
        with self.assertRaises(ValueError):
            Escenario.desde_dict(fila)

    def test_semilla_faltante(self):
        fila = {"id": "ESC-001", "prob_gol_a": 0.5, "prob_gol_b": 0.5,
                "repeticiones": 10, "semilla": ""}
        with self.assertRaises(ValueError):
            Escenario.desde_dict(fila)

    def test_csv_y_json_dan_los_mismos_escenarios(self):
        desde_csv = [Escenario.desde_dict(f).a_dict()
                     for f in FuenteCSV().cargar(DATA / "escenarios.csv")]
        desde_json = [Escenario.desde_dict(f).a_dict()
                      for f in FuenteJSON().cargar(DATA / "escenarios.json")]
        self.assertEqual(desde_csv, desde_json)


if __name__ == "__main__":
    unittest.main()