import tempfile
import unittest
from pathlib import Path

from src.fuentes import FuenteCSV, FuenteJSON
from src.pipeline import (ejecutar_escenario, guardar_rechazos,
                          limpiar_escenarios, resumir_experimento, seleccionar,
                          validar_esquema)

DATA = Path(__file__).resolve().parent.parent / "data"


def _fila(**cambios):
    fila = {"id": "ESC-001", "prob_gol_a": "0.75", "prob_gol_b": "0.70",
            "repeticiones": "10", "semilla": "1"}
    fila.update(cambios)
    return fila


FILAS = [
    _fila(),                          # 1 valida
    _fila(id="ESC-1"),                # 2 id con formato invalido
    _fila(),                          # 3 id repetido
    _fila(id="ESC-002", prob_gol_a="1.5"),   # 4 probabilidad fuera de rango
    _fila(id="ESC-003", semilla=""),         # 5 sin semilla
    _fila(id="ESC-004"),              # 6 valida
]


class TestLimpieza(unittest.TestCase):
    def test_separa_validos_y_rechazados(self):
        validos, rechazos = limpiar_escenarios(FILAS)
        self.assertEqual([e.id for e in validos], ["ESC-001", "ESC-004"])
        self.assertEqual(len(rechazos), 4)

    def test_rechazo_indica_fila_y_motivo(self):
        _, rechazos = limpiar_escenarios(FILAS)
        self.assertEqual([r["fila"] for r in rechazos], [2, 3, 4, 5])
        self.assertIn("repetido", rechazos[1]["motivo"])

    def test_validar_esquema_columna_faltante(self):
        with self.assertRaises(ValueError):
            validar_esquema([{"id": "ESC-001"}])
        with self.assertRaises(ValueError):
            validar_esquema([])

    def test_seleccionar_id_inexistente(self):
        validos, _ = limpiar_escenarios(FILAS)
        with self.assertRaises(ValueError):
            seleccionar(validos, "ESC-999")
        self.assertEqual(len(seleccionar(validos)), 2)

    def test_csv_y_json_dan_mismo_resumen(self):
        resumenes = []
        for fuente, nombre in ((FuenteCSV(), "escenarios.csv"),
                               (FuenteJSON(), "escenarios.json")):
            filas = fuente.cargar(DATA / nombre)
            validos, _ = limpiar_escenarios(filas)
            resumenes.append([resumir_experimento(ejecutar_escenario(e))
                              for e in validos])
        self.assertEqual(resumenes[0], resumenes[1])

    def test_guardar_rechazos(self):
        _, rechazos = limpiar_escenarios(FILAS)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = guardar_rechazos(rechazos, carpeta)
            lineas = ruta.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lineas), 5)  # encabezado + 4 rechazos

    def test_archivo_con_errores_de_ejemplo(self):
        filas = FuenteCSV().cargar(DATA / "escenarios_con_errores.csv")
        validos, rechazos = limpiar_escenarios(filas)
        self.assertEqual([e.id for e in validos], ["ESC-001", "ESC-006"])
        self.assertEqual([r["fila"] for r in rechazos], [2, 3, 4, 5, 6, 7])       


if __name__ == "__main__":
    unittest.main()