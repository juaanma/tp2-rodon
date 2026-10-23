import json
import tempfile
import unittest
from pathlib import Path

from src.modelos import Escenario
from src.pipeline import (ejecutar_escenario, guardar_experimento,
                          resumir_experimento)


class TestPipeline(unittest.TestCase):
    def test_extremos_a_siempre_gana(self):
        esc = Escenario("ESC-003", 1.0, 0.0, 100, 1)
        for tanda in ejecutar_escenario(esc):
            self.assertEqual(tanda["ganador"], "A")
            self.assertEqual(tanda["goles_a"], 5)
            self.assertEqual(tanda["goles_b"], 0)

    def test_misma_semilla_mismo_resultado(self):
        esc = Escenario("ESC-001", 0.75, 0.70, 50, 42)
        self.assertEqual(ejecutar_escenario(esc), ejecutar_escenario(esc))

    def test_cantidad_de_tandas(self):
        esc = Escenario("ESC-004", 0.5, 0.5, 120, 99)
        self.assertEqual(len(ejecutar_escenario(esc)), 120)

    def test_siempre_hay_ganador_consistente(self):
        esc = Escenario("ESC-004", 0.5, 0.5, 200, 99)
        for t in ejecutar_escenario(esc):
            self.assertNotEqual(t["goles_a"], t["goles_b"])
            esperado = "A" if t["goles_a"] > t["goles_b"] else "B"
            self.assertEqual(t["ganador"], esperado)
            self.assertGreaterEqual(t["penales_pateados"], 5)

    def test_resumen_con_valores_conocidos(self):
        tandas = [{"ganador": "A", "penales_pateados": 5},
                  {"ganador": "A", "penales_pateados": 5},
                  {"ganador": "A", "penales_pateados": 6},
                  {"ganador": "B", "penales_pateados": 5}]
        r = resumir_experimento(tandas)
        self.assertEqual(r["porcentaje_a"], 75.0)
        self.assertEqual(r["porcentaje_b"], 25.0)
        self.assertEqual(r["promedio_penales"], 5.25)

    def test_resumen_vacio_da_error(self):
        with self.assertRaises(ValueError):
            resumir_experimento([])

    def test_guardar_crea_archivos_sin_pisar_otros(self):
        a = Escenario("ESC-001", 0.75, 0.70, 10, 42)
        b = Escenario("ESC-002", 0.75, 0.75, 10, 7)
        with tempfile.TemporaryDirectory() as carpeta:
            guardar_experimento(a, ejecutar_escenario(a), carpeta)
            guardar_experimento(b, ejecutar_escenario(b), carpeta)
            for nombre in ("ESC-001_tandas.csv", "ESC-001_resumen.json",
                           "ESC-002_tandas.csv", "ESC-002_resumen.json"):
                self.assertTrue((Path(carpeta) / nombre).exists())
            with open(Path(carpeta) / "ESC-001_resumen.json",
                      encoding="utf-8") as f:
                self.assertEqual(json.load(f)["escenario"]["semilla"], 42)


if __name__ == "__main__":
    unittest.main()