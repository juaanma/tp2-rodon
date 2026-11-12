"""Pruebas de punta a punta: ejecutan el programa como lo haría el usuario."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.main import main
from tests.utilidades import DATA


def ejecutar(*argumentos):
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(salida):
        codigo = main(list(argumentos))
    return codigo, salida.getvalue()


class TestMain(unittest.TestCase):
    def test_historico_genera_archivos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            codigo, texto = ejecutar("historico", "--historico",
                                     str(DATA / "tandas_historicas.json"),
                                     "--salida", carpeta)
            self.assertEqual(codigo, 0)
            self.assertIn("97 tandas", texto)
            resumen = json.loads((Path(carpeta) / "historico_resumen.json")
                                 .read_text(encoding="utf-8"))
            self.assertEqual(resumen["general"]["penales_pateados"], 935)

    def test_simular_es_reproducible(self):
        with tempfile.TemporaryDirectory() as carpeta:
            args = ["simular", "--historico", str(DATA / "tandas_historicas.csv"),
                    "--planteles", str(DATA / "planteles.csv"), "--equipo", "NOR",
                    "--rival", "SUR", "--repeticiones", "300", "--salida", carpeta]
            _, primero = ejecutar(*args)
            _, segundo = ejecutar(*args)
            self.assertIn("Probabilidad de ganar", primero)
            self.assertEqual(primero, segundo)

    def test_errores_se_informan_sin_traceback(self):
        with tempfile.TemporaryDirectory() as carpeta:
            codigo, texto = ejecutar("historico", "--historico", "no_existe.csv",
                                     "--salida", carpeta)
            self.assertEqual(codigo, 1)
            self.assertIn("Error: No se encontró", texto)
            codigo, texto = ejecutar(
                "simular", "--historico", str(DATA / "tandas_historicas.csv"),
                "--planteles", str(DATA / "planteles.csv"), "--equipo", "NOR",
                "--rival", "XXX", "--salida", carpeta)
            self.assertEqual(codigo, 1)
            self.assertIn("disponibles: NOR, SUR", texto)


if __name__ == "__main__":
    unittest.main()
