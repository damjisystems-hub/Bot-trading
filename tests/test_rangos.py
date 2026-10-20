import unittest

from crt.rangos import Evento, escenario, evaluar, semaforo
from crt.velas import Vela
from tests.ayuda import ny

T = ny("2025-03-04 05:00")


def vela(o, h, l, c, i=1):
    return Vela(T, o, h, l, c, i, i)


V1 = vela(106, 110, 100, 105, i=0)


class QueFormaLaVela2(unittest.TestCase):
    def test_rango_alcista(self):
        e = evaluar(V1, vela(105, 105, 97, 103), "H4")
        self.assertEqual((e.tipo, e.direccion, e.objetivo, e.barrido), ("rango", +1, 110, 97))

    def test_rango_bajista(self):
        e = evaluar(V1, vela(105, 112, 104, 106), "H4")
        self.assertEqual((e.tipo, e.direccion, e.objetivo, e.barrido), ("rango", -1, 100, 112))

    def test_si_cierra_fuera_es_una_ruptura(self):
        self.assertEqual((evaluar(V1, vela(105, 112, 104, 111), "H4").tipo, evaluar(V1, vela(105, 112, 104, 111), "H4").direccion), ("ruptura", +1))
        self.assertEqual(evaluar(V1, vela(105, 106, 96, 98), "H4").direccion, -1)

    def test_vela_interior_o_que_toma_los_dos_lados_no_forma_nada(self):
        self.assertIsNone(evaluar(V1, vela(105, 108, 102, 104), "H4"))
        self.assertIsNone(evaluar(V1, vela(105, 112, 97, 104), "H4"))


class CierreUnPocoFuera(unittest.TestCase):
    """Regla candidata del diario: el autor da por bueno un rango que cierra muy poco por fuera."""

    def test_sin_tolerancia_es_una_ruptura(self):
        self.assertEqual(evaluar(V1, vela(105, 105, 98, 99.5), "D1").tipo, "ruptura")

    def test_con_tolerancia_sigue_siendo_un_rango(self):
        # La vela 1 mide 10; con el 10 %, cerrar hasta 1 punto por debajo de 100 aún vale.
        e = evaluar(V1, vela(105, 105, 98, 99.5), "D1", tolerancia=0.1)
        self.assertEqual((e.tipo, e.direccion, e.objetivo, e.barrido), ("rango", +1, 110, 98))
        self.assertEqual(evaluar(V1, vela(105, 105, 98, 98.5), "D1", tolerancia=0.1).tipo, "ruptura")  # demasiado fuera
        e = evaluar(V1, vela(105, 111.5, 104, 110.8), "D1", tolerancia=0.1)
        self.assertEqual((e.tipo, e.direccion, e.barrido), ("rango", -1, 111.5))

    def test_si_toma_los_dos_lados_y_cierra_fuera_sigue_siendo_ruptura(self):
        self.assertEqual(evaluar(V1, vela(105, 111, 99, 110.5), "D1", tolerancia=0.1).tipo, "ruptura")


class VidaDeUnRango(unittest.TestCase):
    def test_se_completa_al_tocar_el_objetivo(self):
        e = evaluar(V1, vela(105, 105, 97, 103), "H4")
        e.actualizar_con_barra(vela(103, 109, 102, 108))
        self.assertEqual(e.estado, "activo")
        e.actualizar_con_barra(vela(108, 110, 107, 109))
        self.assertEqual((e.estado, e.velas_hasta_completar), ("completado", 1))

    def test_una_mecha_no_lo_anula_pero_un_cierre_si(self):
        e = evaluar(V1, vela(105, 105, 97, 103), "H4")
        e.actualizar_con_cierre(vela(103, 104, 95, 98))  # mecha por debajo de 97, cierre por encima
        self.assertEqual(e.estado, "activo")
        e.actualizar_con_cierre(vela(98, 99, 94, 96))
        self.assertEqual(e.estado, "anulado")


class Semaforo(unittest.TestCase):
    def test_colores(self):
        alcista = evaluar(V1, vela(105, 105, 97, 103), "H4")
        self.assertEqual(semaforo(alcista, +1), "verde")
        self.assertEqual(semaforo(alcista, -1), "rojo")
        alcista.estado = "completado"
        self.assertEqual(semaforo(alcista, +1), "ambar")
        ruptura_bajista = evaluar(V1, vela(105, 106, 96, 98), "H4")
        self.assertEqual(semaforo(ruptura_bajista, +1), "rojo")
        self.assertEqual(semaforo(ruptura_bajista, -1), "ambar")
        self.assertEqual(semaforo(None, +1), "ambar")

    def test_escenarios_del_primer_video(self):
        bajista = Evento("H4", "rango", -1, 0, 0, objetivo=100, barrido=112)
        self.assertEqual(escenario(bajista, +1), "3")  # aún sin completar
        bajista.estado, bajista.velas_hasta_completar = "completado", 1
        self.assertEqual(escenario(bajista, +1), "2")
        bajista.velas_hasta_completar = 3
        self.assertEqual(escenario(bajista, +1), "1")
        self.assertEqual(escenario(None, +1), "otro")


if __name__ == "__main__":
    unittest.main()
