import unittest

from crt import diagnostico
from tests.ayuda import SIN_COSTES, camino, espejo
from tests.test_motor import HASTA_LAS_9

# A las 9:00 se forma un rango alcista de 4H: vela 1 de 100 a 110, la vela 2 barre hasta 97 y cierra en 103.
# Entrando al cierre (103) con el stop en 97 y el TP en 110, el objetivo está a 7 / 6 R.


class RangosEnBruto(unittest.TestCase):
    def _unico(self, puntos):
        hechos = [h for h in diagnostico.rangos_en_bruto(camino(puntos), SIN_COSTES) if h.objetivo_r == 7 / 6]
        self.assertEqual(len(hechos), 1)
        return hechos[0]

    def test_llega_al_objetivo(self):
        self.assertAlmostEqual(self._unico(HASTA_LAS_9 + [("2025-03-04 11:00", 111)]).r, 7 / 6)

    def test_toca_el_barrido(self):
        self.assertEqual(self._unico(HASTA_LAS_9 + [("2025-03-04 11:00", 96)]).r, -1.0)

    def test_en_ventas_es_lo_mismo_al_reves(self):
        hechos = diagnostico.rangos_en_bruto(camino(espejo(HASTA_LAS_9 + [("2025-03-04 11:00", 111)])), SIN_COSTES)
        ventas = [h for h in hechos if h.direccion < 0 and abs(h.objetivo_r - 7 / 6) < 1e-9]
        self.assertEqual([round(h.r, 6) for h in ventas], [round(7 / 6, 6)])

    def test_el_texto_compara_con_el_azar(self):
        hechos = diagnostico.rangos_en_bruto(camino(HASTA_LAS_9 + [("2025-03-04 11:00", 111)]), SIN_COSTES)
        self.assertIn("al azar", diagnostico.texto("PRUEBA", "H4", hechos))


if __name__ == "__main__":
    unittest.main()
