import unittest
from datetime import time

from crt.entrada import es_order_block, hora_permitida, sesion
from crt.velas import Vela
from tests.ayuda import ny

T = ny("2025-03-04 09:00")


def vela(o, c):
    return Vela(T, o, max(o, c), min(o, c), c)


class OrderBlock(unittest.TestCase):
    def test_verde_mas_fuerte_que_la_roja_anterior(self):
        self.assertTrue(es_order_block(vela(103, 102.5), vela(102.5, 104), +1))

    def test_no_vale_si_el_cuerpo_no_es_mas_grande(self):
        self.assertFalse(es_order_block(vela(103, 102), vela(102, 103), +1))

    def test_no_vale_si_no_cierra_por_encima_de_donde_abrio_la_roja(self):
        # cuerpo más grande, pero abre muy abajo y no pasa de 103
        self.assertFalse(es_order_block(vela(103, 102.5), vela(101, 102.9), +1))

    def test_ventas_al_reves(self):
        self.assertTrue(es_order_block(vela(97, 97.5), vela(97.5, 96), -1))
        self.assertFalse(es_order_block(vela(97, 97.5), vela(97.5, 96), +1))


class Horario(unittest.TestCase):
    def permitida(self, hora, espera=45, solo_tras_apertura=False):
        return hora_permitida(ny(f"2025-03-04 {hora}"), time(1, 0), time(13, 0), espera, solo_tras_apertura)

    def test_espera_de_45_minutos_tras_la_apertura(self):
        self.assertTrue(self.permitida("09:30"))
        self.assertFalse(self.permitida("09:45"))
        self.assertFalse(self.permitida("10:00"))
        self.assertTrue(self.permitida("10:15"))
        self.assertTrue(self.permitida("09:45", espera=0))

    def test_horario_de_1_a_13(self):
        self.assertFalse(self.permitida("01:00"))
        self.assertTrue(self.permitida("01:15"))
        self.assertTrue(self.permitida("13:00"))
        self.assertFalse(self.permitida("13:15"))

    def test_solo_despues_de_la_apertura(self):
        self.assertFalse(self.permitida("09:00", solo_tras_apertura=True))
        self.assertTrue(self.permitida("10:30", solo_tras_apertura=True))

    def test_sesion(self):
        self.assertEqual(sesion(ny("2025-03-04 09:30")), "Londres")
        self.assertEqual(sesion(ny("2025-03-04 10:30")), "Tras la apertura")


if __name__ == "__main__":
    unittest.main()
