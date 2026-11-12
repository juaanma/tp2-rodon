import random
import unittest

from src.modelos import Arquero, Equipo, Pateador, resultado_posible
from src.pipeline import verificar_ranking
from src.simulacion import (ModeloPenales, calibrar_efectividad,
                            diferencia_pareada, equipo_homogeneo,
                            intervalo_proporcion, recomendar_orden,
                            simular_enfrentamiento)


def equipo(codigo, efectividades, temples=None, factor=0.0):
    temples = temples or [0.5] * len(efectividades)
    pateadores = [Pateador(f"{codigo}{i}", e, t)
                  for i, (e, t) in enumerate(zip(efectividades, temples), start=1)]
    return Equipo(codigo, codigo, pateadores, Arquero(f"Arq{codigo}", factor))


class TestSimulacion(unittest.TestCase):
    def test_misma_semilla_mismo_resultado(self):
        a, b = equipo("AAA", [0.8] * 6), equipo("BBB", [0.7] * 6)
        modelo = ModeloPenales()
        uno = simular_enfrentamiento(modelo, a, b, 300, semilla=5)
        dos = simular_enfrentamiento(modelo, a, b, 300, semilla=5)
        self.assertEqual(uno, dos)

    def test_caso_extremo_termina_lo_antes_posible(self):
        # A siempre convierte (0.99 por el límite del arquero) y B nunca (0.01)
        a, b = equipo("AAA", [1.0] * 5), equipo("BBB", [0.0] * 5)
        modelo = ModeloPenales(presion=0)
        rng = random.Random(0)
        r = modelo.simular_tanda(a, a.pateadores, b, b.pateadores, rng)
        # A patea primero. Tras 3 penales cada uno va 3-0 y a B le quedan 2:
        # ya no puede alcanzarlo, así que la tanda termina con 6 tiros.
        self.assertEqual((r["goles_1"], r["goles_2"], r["tiros_1"], r["tiros_2"]),
                         (3, 0, 3, 3))

    def test_toda_tanda_simulada_cumple_el_reglamento(self):
        """Propiedad: el simulador nunca produce un marcador que el validador
        de datos reales rechazaría."""
        a, b = equipo("AAA", [0.75] * 6), equipo("BBB", [0.7] * 6)
        tandas, _ = simular_enfrentamiento(ModeloPenales(), a, b, 2000, semilla=1)
        for t in tandas:
            ganador = (t["goles_a"], t["tiros_a"]) if t["gana_a"] else (t["goles_b"], t["tiros_b"])
            perdedor = (t["goles_b"], t["tiros_b"]) if t["gana_a"] else (t["goles_a"], t["tiros_a"])
            self.assertTrue(resultado_posible(*ganador, *perdedor), t)

    def test_temple_maximo_anula_la_presion(self):
        """Con temple 1 la presión no influye: mismo resultado exacto que sin presión."""
        a = equipo("AAA", [0.85, 0.8, 0.75, 0.7, 0.65], [1.0] * 5)
        b = equipo("BBB", [0.8] * 5, [1.0] * 5)
        con = simular_enfrentamiento(ModeloPenales(0.4), a, b, 500, semilla=3)
        sin = simular_enfrentamiento(ModeloPenales(0.0), a, b, 500, semilla=3)
        self.assertEqual(con, sin)

    def test_empieza_A_se_respeta(self):
        a, b = equipo("AAA", [0.8] * 5), equipo("BBB", [0.8] * 5)
        tandas, _ = simular_enfrentamiento(ModeloPenales(), a, b, 50, 1, empieza="A")
        self.assertTrue(all(t["a_pateo_primero"] for t in tandas))
        with self.assertRaises(ValueError):
            simular_enfrentamiento(ModeloPenales(), a, b, 5, 1, empieza="X")

    def test_parametros_invalidos(self):
        a, b = equipo("AAA", [0.8] * 5), equipo("BBB", [0.8] * 5)
        with self.assertRaises(ValueError):
            simular_enfrentamiento(ModeloPenales(), a, b, 0, 1)
        with self.assertRaises(ValueError):
            ModeloPenales(presion=1.5)


class TestRecomendarOrden(unittest.TestCase):
    def test_ranking_completo_y_ordenado(self):
        a = equipo("AAA", [0.85, 0.82, 0.8, 0.78, 0.76, 0.7],
                   [0.2, 0.9, 0.5, 0.8, 0.3, 0.5])
        b = equipo("BBB", [0.78] * 6)
        ranking = recomendar_orden(ModeloPenales(), a, b, a.mejores(), 100, 7)
        verificar_ranking(ranking)  # 120 órdenes distintos y probabilidades válidas
        probs = [r["prob_ganar"] for r in ranking]
        self.assertEqual(probs, sorted(probs, reverse=True))
        self.assertEqual(ranking[0]["posicion"], 1)

    def test_hay_que_elegir_cinco(self):
        a, b = equipo("AAA", [0.8] * 6), equipo("BBB", [0.8] * 6)
        with self.assertRaises(ValueError):
            recomendar_orden(ModeloPenales(), a, b, a.pateadores[:4], 10, 1)


class TestEstadistica(unittest.TestCase):
    def test_intervalo_conocido(self):
        ic = intervalo_proporcion(50, 100)
        self.assertEqual(ic["proporcion"], 0.5)
        self.assertAlmostEqual(ic["ic_inferior"], 0.402, places=3)
        with self.assertRaises(ValueError):
            intervalo_proporcion(0, 0)

    def test_diferencia_pareada(self):
        r = diferencia_pareada([True, True, False, True], [True, False, False, False])
        self.assertEqual(r["diferencia"], 0.5)
        with self.assertRaises(ValueError):
            diferencia_pareada([True], [True, False])

    def test_calibracion_sin_presion_devuelve_la_conversion(self):
        base = calibrar_efectividad(ModeloPenales(0), 0.73, repeticiones=2000)
        self.assertAlmostEqual(base, 0.73, delta=0.01)

    def test_calibracion_con_presion_compensa(self):
        """Con presión, la efectividad base debe ser mayor que la conversión
        observada, y al simular con ella se recupera la conversión."""
        modelo = ModeloPenales(0.25)
        base = calibrar_efectividad(modelo, 0.73, repeticiones=2000)
        self.assertGreater(base, 0.73)
        _, resumen = simular_enfrentamiento(
            modelo, equipo_homogeneo("AAA", base), equipo_homogeneo("BBB", base),
            2000, semilla=2026)
        self.assertAlmostEqual(resumen["conversion"], 0.73, delta=0.01)


if __name__ == "__main__":
    unittest.main()
