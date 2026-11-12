import unittest

from src.modelos import (Arquero, Equipo, Pateador, TandaHistorica,
                         resultado_posible, tanda_decidida)
from tests.utilidades import fila_tanda


class TestReglasDeLaTanda(unittest.TestCase):
    def test_termina_cuando_el_rival_no_puede_alcanzar(self):
        # A (primero) 3/3, B 0/2: a B le quedan 3 y como mucho llega a 3 -> sigue
        self.assertFalse(tanda_decidida(3, 3, 0, 2))
        # A 3/3, B 0/3: a B le quedan 2 -> no alcanza a 3
        self.assertTrue(tanda_decidida(3, 3, 0, 3))

    def test_empate_tras_cinco_va_a_muerte_subita(self):
        self.assertFalse(tanda_decidida(4, 5, 4, 5))
        self.assertFalse(tanda_decidida(5, 6, 4, 5))  # falta patear B
        self.assertTrue(tanda_decidida(5, 6, 4, 6))

    def test_marcadores_reales_son_posibles(self):
        self.assertTrue(resultado_posible(4, 4, 2, 4))   # final Mundial 2022
        self.assertTrue(resultado_posible(9, 9, 8, 9))   # Euro 1980, 18 tiros
        self.assertTrue(resultado_posible(3, 3, 0, 3))   # Portugal-Eslovenia 2024

    def test_marcadores_imposibles(self):
        self.assertFalse(resultado_posible(5, 5, 3, 5))  # termina antes del 5.º
        self.assertFalse(resultado_posible(6, 6, 4, 6))  # en muerte súbita gana por 1
        self.assertFalse(resultado_posible(4, 4, 2, 2))  # diferencia de 2 tiros


class TestTandaHistorica(unittest.TestCase):
    def test_tanda_valida_desde_texto(self):
        t = TandaHistorica.desde_dict(fila_tanda())
        self.assertEqual(t.anio, 2022)
        self.assertEqual(t.total_tiros(), 8)
        self.assertAlmostEqual(t.conversion(), 0.75)
        self.assertFalse(t.llego_a_muerte_subita())

    def test_regex_rechaza_id_mal_formado(self):
        for id_malo in ("MUN-22-01", "XXX-2022-01", "MUN-2022-1", "mun-2022-05"):
            with self.subTest(id=id_malo):
                with self.assertRaises(ValueError):
                    TandaHistorica.desde_dict(fila_tanda(id=id_malo))

    def test_id_debe_coincidir_con_torneo_y_anio(self):
        with self.assertRaises(ValueError):
            TandaHistorica.desde_dict(fila_tanda(torneo="Eurocopa"))
        with self.assertRaises(ValueError):
            TandaHistorica.desde_dict(fila_tanda(anio="2018"))

    def test_partido_sin_empate_no_tiene_penales(self):
        with self.assertRaises(ValueError):
            TandaHistorica.desde_dict(fila_tanda(resultado_partido="3-2"))

    def test_no_se_convierten_mas_penales_que_los_pateados(self):
        with self.assertRaises(ValueError):
            TandaHistorica.desde_dict(fila_tanda(goles_ganador="5"))

    def test_campo_faltante_o_vacio(self):
        fila = fila_tanda()
        del fila["ronda"]
        with self.assertRaises(ValueError):
            TandaHistorica.desde_dict(fila)
        with self.assertRaises(ValueError):
            TandaHistorica.desde_dict(fila_tanda(perdedor="  "))

    def test_quien_pateo_primero(self):
        uno_mas = TandaHistorica.desde_dict(fila_tanda(
            resultado_partido="1-1", goles_ganador="3", goles_perdedor="1",
            tiros_ganador="3", tiros_perdedor="4"))
        self.assertEqual(uno_mas.pateo_primero(), "perdedor")
        self.assertIsNone(TandaHistorica.desde_dict(fila_tanda()).pateo_primero())


class TestJugadores(unittest.TestCase):
    def test_presion_segun_temple(self):
        frio = Pateador("A", 0.8, temple=1.0)
        nervioso = Pateador("B", 0.8, temple=0.0)
        self.assertAlmostEqual(frio.efectividad_bajo_presion(0.25), 0.8)
        self.assertAlmostEqual(nervioso.efectividad_bajo_presion(0.25), 0.6)

    def test_efectividad_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            Pateador("A", 1.2)
        with self.assertRaises(ValueError):
            Pateador("A", "nan")

    def test_arquero_ajusta_y_acota(self):
        self.assertAlmostEqual(Arquero("X", 0.05).ajustar(0.80), 0.75)
        self.assertEqual(Arquero("X", -0.2).ajustar(0.95), 0.99)
        with self.assertRaises(ValueError):
            Arquero("X", 0.5)

    def test_equipo_necesita_cinco_pateadores_y_codigo_valido(self):
        cinco = [Pateador(f"P{i}", 0.7) for i in range(5)]
        with self.assertRaises(ValueError):
            Equipo("NOR", "Norte", cinco[:4], Arquero("X"))
        with self.assertRaises(ValueError):
            Equipo("Norte", "Norte", cinco, Arquero("X"))
        equipo = Equipo("NOR", "Norte", cinco + [Pateador("Z", 0.9)], Arquero("X"))
        self.assertEqual(equipo.mejores()[0].nombre, "Z")
        self.assertEqual(len(equipo.orden_completo(equipo.mejores())), 6)


if __name__ == "__main__":
    unittest.main()
