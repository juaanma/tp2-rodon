import tempfile
import unittest
from pathlib import Path

from src.fuentes import FuenteCSV, FuenteJSON
from src.pipeline import (COLUMNAS_HISTORICO, analizar_historico,
                          construir_equipos, elegir_pateadores,
                          filtrar_historico, guardar_csv, inspeccionar,
                          limpiar_historico, validar_esquema)
from tests.utilidades import DATA, fila_tanda


def historico(nombre="tandas_historicas.csv"):
    fuente = FuenteCSV() if nombre.endswith(".csv") else FuenteJSON()
    return limpiar_historico(fuente.cargar(DATA / nombre))


class TestLimpieza(unittest.TestCase):
    def test_datos_reales_sin_rechazos(self):
        validas, rechazos = historico()
        self.assertEqual(len(validas), 97)
        self.assertEqual(rechazos, [])

    def test_archivo_con_errores_registra_cada_rechazo(self):
        validas, rechazos = historico("tandas_con_errores.csv")
        self.assertEqual([t.id for t in validas], ["MUN-2022-05", "CAM-2019-01"])
        self.assertEqual([r["registro"] for r in rechazos], list(range(2, 12)))
        self.assertTrue(all(r["motivo"] for r in rechazos))

    def test_duplicado_con_otro_id(self):
        filas = [fila_tanda(), fila_tanda(id="MUN-2022-09")]
        validas, rechazos = limpiar_historico(filas)
        self.assertEqual(len(validas), 1)
        self.assertIn("duplicado", rechazos[0]["motivo"])

    def test_esquema_sin_columna_obligatoria(self):
        filas = [{k: v for k, v in fila_tanda().items() if k != "tiros_ganador"}]
        with self.assertRaises(ValueError):
            validar_esquema(filas, COLUMNAS_HISTORICO)
        with self.assertRaises(ValueError):
            validar_esquema([], COLUMNAS_HISTORICO)

    def test_inspeccion_cuenta_vacios(self):
        info = inspeccionar([fila_tanda(), fila_tanda(perdedor="")])
        self.assertEqual(info["registros"], 2)
        self.assertEqual(info["vacios_por_columna"]["perdedor"], 1)


class TestAnalisis(unittest.TestCase):
    def test_valores_conocidos(self):
        filas = [fila_tanda(),  # 4/4 y 2/4 -> 6 de 8, sin muerte súbita
                 fila_tanda(id="EUR-1980-01", torneo="Eurocopa", anio="1980",
                            ronda="3/4", ganador="Czechoslovakia", perdedor="Italy",
                            resultado_partido="1-1", goles_ganador="9",
                            goles_perdedor="8", tiros_ganador="9",
                            tiros_perdedor="9")]  # 17 de 18, muerte súbita
        tandas, _ = limpiar_historico(filas)
        general = analizar_historico(tandas)["general"]
        self.assertEqual(general["penales_pateados"], 26)
        self.assertEqual(general["penales_convertidos"], 23)
        self.assertAlmostEqual(general["conversion"], round(23 / 26, 4))
        self.assertEqual(general["prop_muerte_subita"], 0.5)
        self.assertEqual(general["tiros_promedio"], 13.0)

    def test_los_grupos_conservan_los_totales(self):
        """Propiedad: sumar los grupos por torneo da el total general."""
        tandas, _ = historico()
        analisis = analizar_historico(tandas)
        torneos = [g for g in analisis["por_grupo"] if g["agrupacion"] == "torneo"]
        for campo in ("tandas", "penales_pateados", "penales_convertidos"):
            self.assertEqual(sum(g[campo] for g in torneos),
                             analisis["general"][campo])
        self.assertEqual(sum(analisis["distribucion_tiros_totales"].values()), 97)

    def test_csv_y_json_dan_el_mismo_analisis(self):
        self.assertEqual(analizar_historico(historico()[0]),
                         analizar_historico(historico("tandas_historicas.json")[0]))

    def test_filtros(self):
        tandas, _ = historico()
        copa = filtrar_historico(tandas, torneo="Copa America", desde=2015, hasta=2016)
        self.assertEqual(len(copa), 5)
        self.assertEqual(filtrar_historico(tandas, desde=2030), [])
        with self.assertRaises(ValueError):
            analizar_historico([])
        with self.assertRaises(ValueError):
            filtrar_historico(tandas, desde=2020, hasta=2010)


class TestPlanteles(unittest.TestCase):
    def test_faltantes_se_completan_de_forma_explicita(self):
        filas = FuenteCSV().cargar(DATA / "planteles.csv")
        equipos, rechazos = construir_equipos(filas, efectividad_por_defecto=0.74)
        self.assertEqual(sorted(equipos), ["NOR", "SUR"])
        self.assertEqual(rechazos, [])
        funes = equipos["NOR"].pateador("Funes")
        self.assertEqual(funes.efectividad, 0.74)
        self.assertTrue(funes.efectividad_estimada)
        self.assertEqual(equipos["NOR"].pateador("Gimenez").temple, 0.5)
        self.assertEqual(equipos["SUR"].arquero.factor_atajada, -0.02)

    def test_csv_y_json_dan_los_mismos_equipos(self):
        def resumen(fuente, nombre):
            equipos, _ = construir_equipos(fuente.cargar(DATA / nombre), 0.74)
            return {c: [(p.nombre, p.efectividad, p.temple) for p in e.pateadores]
                    for c, e in equipos.items()}
        self.assertEqual(resumen(FuenteCSV(), "planteles.csv"),
                         resumen(FuenteJSON(), "planteles.json"))

    def test_fila_invalida_y_equipo_incompleto(self):
        filas = [{"codigo_equipo": "AAA", "equipo": "A", "rol": "pateador",
                  "nombre": f"P{i}", "efectividad": "0.8", "temple": "",
                  "factor_atajada": ""} for i in range(5)]
        filas.append({"codigo_equipo": "AAA", "equipo": "A", "rol": "pateador",
                      "nombre": "Malo", "efectividad": "1.4", "temple": "",
                      "factor_atajada": ""})
        equipos, rechazos = construir_equipos(filas, 0.74)
        self.assertEqual(equipos, {})  # sin arquero
        motivos = " | ".join(r["motivo"] for r in rechazos)
        self.assertIn("efectividad de Malo", motivos)
        self.assertIn("arquero", motivos)

    def test_elegir_pateadores(self):
        equipos, _ = construir_equipos(FuenteCSV().cargar(DATA / "planteles.csv"), 0.74)
        nor = equipos["NOR"]
        self.assertEqual([p.nombre for p in elegir_pateadores(nor)],
                         ["Acosta", "Benitez", "Castro", "Dominguez", "Escobar"])
        with self.assertRaises(ValueError):
            elegir_pateadores(nor, ["Acosta", "Benitez"])
        with self.assertRaises(ValueError):
            elegir_pateadores(nor, ["Acosta", "Benitez", "Castro", "Dominguez", "Nadie"])

    def test_guardar_csv(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = guardar_csv([{"a": 1}, {"a": 2}], Path(carpeta) / "x" / "t.csv")
            self.assertEqual(ruta.read_text(encoding="utf-8").split(), ["a", "1", "2"])


if __name__ == "__main__":
    unittest.main()
