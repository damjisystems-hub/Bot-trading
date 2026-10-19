import unittest

from crt.marcos import Marco
from crt.motor import Ajustes, Operacion, _revisar_salida, probar, sesgo_de_fondo
from crt.rangos import Evento
from crt.velas import Vela
from tests.ayuda import SIN_COSTES, camino, espejo, ny

# Martes 4-3-2025, hora de Nueva York. La vela de 4H de la 1 (106-110-100-105) es la vela 1; la de
# las 5 baja a 97, barre el mínimo de 100 y cierra dentro a 103: rango alcista con objetivo 110 y
# barrido en 97, formado a las 9:00. En 1H no se forma ningún rango alcista antes de las 9:00.
HASTA_LAS_9 = [
    ("2025-03-03 21:00", 104),
    ("2025-03-04 01:00", 106),
    ("2025-03-04 02:00", 110),
    ("2025-03-04 04:00", 100),
    ("2025-03-04 05:00", 105),
    ("2025-03-04 06:00", 103),
    ("2025-03-04 07:00", 101),
    ("2025-03-04 08:00", 97),
    ("2025-03-04 09:00", 103),
]
# Order block a las 9:30: roja 103 → 102,5 y verde 102,5 → 104.
ORDER_BLOCK_9_30 = [("2025-03-04 09:15", 102.5), ("2025-03-04 09:30", 104)]

SOLO_4H = Ajustes(sesgo_fijo=+1, diario="ignorar")


class EntradaTrasElCierreDe4H(unittest.TestCase):
    def test_compra_en_el_primer_order_block_y_llega_al_tp(self):
        res = probar(camino(HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125), ("2025-03-04 13:00", 125)]), SIN_COSTES, SOLO_4H)
        self.assertEqual(len(res.operaciones), 1)
        op = res.operaciones[0]
        self.assertEqual(op.hora_entrada, ny("2025-03-04 09:30"))
        self.assertEqual((op.direccion, op.sesion, op.via), (+1, "Londres", "cierre"))
        self.assertAlmostEqual(op.entrada, 104)
        self.assertAlmostEqual(op.stop, 97)  # detrás del barrido
        self.assertAlmostEqual(op.tp, 118)  # 1 a 2
        self.assertEqual(op.resultado, "TP")
        self.assertAlmostEqual(op.r, 2.0)

    def test_si_baja_al_barrido_es_stop(self):
        res = probar(camino(HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 10:30", 95), ("2025-03-04 11:00", 96)]), SIN_COSTES, SOLO_4H)
        self.assertEqual([(o.resultado, round(o.r, 6)) for o in res.operaciones], [("SL", -1.0)])

    def test_no_entra_antes_de_que_cierre_la_vela_de_4h_si_1h_no_forma_rango(self):
        # A las 8:30 hay order block, la vela de 4H ya ha barrido el 100 y el precio ha vuelto
        # dentro, pero la vela de 1H de las 7 cierra por debajo de la anterior: no hay rango en 1H.
        puntos = HASTA_LAS_9[:-3] + [
            ("2025-03-04 07:30", 99),
            ("2025-03-04 08:00", 100.6),
            ("2025-03-04 08:15", 100.4),
            ("2025-03-04 08:30", 101.2),
            ("2025-03-04 09:00", 103),
        ]
        res = probar(camino(puntos), SIN_COSTES, SOLO_4H)
        self.assertEqual(res.operaciones, [])

    def test_ventas_al_reves(self):
        puntos = espejo(HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125), ("2025-03-04 13:00", 125)])
        res = probar(camino(puntos), SIN_COSTES, Ajustes(sesgo_fijo=-1, diario="ignorar"))
        self.assertEqual(len(res.operaciones), 1)
        op = res.operaciones[0]
        self.assertEqual((op.direccion, op.resultado), (-1, "TP"))
        self.assertAlmostEqual(op.entrada, 96)
        self.assertAlmostEqual(op.stop, 103)
        self.assertAlmostEqual(op.tp, 82)
        self.assertAlmostEqual(op.r, 2.0)

    def test_sin_sesgo_compras_no_compra(self):
        res = probar(camino(HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125)]), SIN_COSTES, Ajustes(sesgo_fijo=-1, diario="ignorar"))
        self.assertEqual(res.operaciones, [])

    def test_con_el_diario_obligatorio_y_sin_rango_diario_no_entra(self):
        res = probar(camino(HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125)]), SIN_COSTES, Ajustes(sesgo_fijo=+1))
        self.assertEqual(res.operaciones, [])

    def test_tope_de_operaciones_del_dia(self):
        res = probar(camino(HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125)]), SIN_COSTES, Ajustes(sesgo_fijo=+1, diario="ignorar", max_operaciones_dia=0))
        self.assertEqual(res.operaciones, [])
        self.assertEqual(res.descartadas["tope de operaciones del día"], 1)


class DiarioAFavor(unittest.TestCase):
    # El lunes (de domingo 17:00 a lunes 17:00) va de 100 a 110. El martes barre el 100 a las 7:15 y
    # a las 9:00 se forma el rango alcista de 4H: el diario se pone en verde con objetivo en 110.
    LUNES = [("2025-03-02 18:00", 105), ("2025-03-03 03:00", 110), ("2025-03-03 10:00", 100), ("2025-03-03 17:00", 104)]
    PUNTOS = LUNES + HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125)]

    def test_no_entra_si_el_tp_queda_mas_alla_del_objetivo_del_diario(self):
        # TP en 118 y el objetivo del diario en 110
        res = probar(camino(self.PUNTOS), SIN_COSTES, Ajustes(sesgo_fijo=+1))
        self.assertEqual(res.operaciones, [])
        self.assertEqual(res.descartadas["el TP no cabe antes del objetivo del diario"], 1)

    def test_sin_esa_comprobacion_entra(self):
        res = probar(camino(self.PUNTOS), SIN_COSTES, Ajustes(sesgo_fijo=+1, comprobar_objetivo_diario=False))
        self.assertEqual([(o.hora_entrada, o.resultado) for o in res.operaciones], [(ny("2025-03-04 09:30"), "TP")])


class EsperaTrasLaApertura(unittest.TestCase):
    # Primer order block a las 9:45 (dentro de la espera) y el siguiente a las 10:30.
    PUNTOS = HASTA_LAS_9 + [
        ("2025-03-04 09:15", 103.6),
        ("2025-03-04 09:30", 103.2),
        ("2025-03-04 09:45", 104),
        ("2025-03-04 10:00", 104.5),
        ("2025-03-04 10:15", 104.2),
        ("2025-03-04 10:30", 105),
        ("2025-03-04 12:00", 125),
    ]

    def test_salta_el_order_block_de_las_9_45_y_entra_en_el_de_las_10_30(self):
        res = probar(camino(self.PUNTOS), SIN_COSTES, SOLO_4H)
        self.assertEqual(len(res.operaciones), 1)
        op = res.operaciones[0]
        self.assertEqual((op.hora_entrada, op.sesion, op.resultado), (ny("2025-03-04 10:30"), "Tras la apertura", "TP"))
        self.assertAlmostEqual(op.tp, 121)

    def test_sin_espera_entra_a_las_9_45(self):
        res = probar(camino(self.PUNTOS), SIN_COSTES, Ajustes(sesgo_fijo=+1, diario="ignorar", espera_apertura_min=0))
        self.assertEqual([o.hora_entrada for o in res.operaciones], [ny("2025-03-04 09:45")])


class AnticipoCon1H(unittest.TestCase):
    # La vela de 4H de las 5 aún no ha cerrado: barre el mínimo de 100 a las 7:15 y en 1H se forma
    # un rango alcista a las 8:00 (la vela de las 7 baja a 98,5 y cierra a 101, dentro de la de las 6).
    PUNTOS = HASTA_LAS_9[:5] + [
        ("2025-03-04 06:00", 102),
        ("2025-03-04 06:30", 100.5),
        ("2025-03-04 07:00", 101.5),
        ("2025-03-04 07:30", 98.5),
        ("2025-03-04 08:00", 101),
        ("2025-03-04 08:15", 100.8),
        ("2025-03-04 08:30", 101.6),
        ("2025-03-04 10:00", 110),
        ("2025-03-04 10:30", 110),
    ]

    def test_entra_antes_del_cierre_de_4h_y_no_repite_con_el_cierre(self):
        res = probar(camino(self.PUNTOS), SIN_COSTES, SOLO_4H)
        self.assertEqual(len(res.operaciones), 1)
        op = res.operaciones[0]
        self.assertEqual((op.hora_entrada, op.via, op.resultado), (ny("2025-03-04 08:30"), "anticipo", "TP"))
        self.assertAlmostEqual(op.stop, 98.5)
        self.assertAlmostEqual(op.tp, 101.6 + 2 * 3.1)


class CierreDelViernes(unittest.TestCase):
    def test_lo_abierto_se_cierra_el_viernes_a_las_17(self):
        puntos = [(t.replace("2025-03-04", "2025-03-07").replace("2025-03-03", "2025-03-06"), p) for t, p in HASTA_LAS_9 + ORDER_BLOCK_9_30]
        puntos += [("2025-03-07 10:00", 105), ("2025-03-07 17:00", 105)]
        res = probar(camino(puntos), SIN_COSTES, SOLO_4H)
        self.assertEqual(len(res.operaciones), 1)
        op = res.operaciones[0]
        self.assertEqual((op.resultado, op.hora_salida), ("Cierre semanal", ny("2025-03-07 17:00")))
        self.assertAlmostEqual(op.r, 1 / 7)


class Salidas(unittest.TestCase):
    def _compra(self):
        return Operacion(+1, ny("2025-03-04 09:30"), "Londres", "otro", "cierre", entrada=100, stop=95, tp=110, riesgo=5)

    def test_si_en_la_misma_barra_toca_stop_y_tp_cuenta_como_stop(self):
        op = self._compra()
        self.assertTrue(_revisar_salida(op, Vela(ny("2025-03-04 10:00"), 100, 111, 94, 105), SIN_COSTES))
        self.assertEqual((op.resultado, op.r), ("SL", -1.0))

    def test_si_abre_por_debajo_del_stop_sale_a_la_apertura(self):
        op = self._compra()
        _revisar_salida(op, Vela(ny("2025-03-04 10:00"), 93, 94, 92, 93.5), SIN_COSTES)
        self.assertAlmostEqual(op.r, -1.4)


class SesgoDeFondo(unittest.TestCase):
    def _marco(self, evento):
        m = Marco("W1")
        m.ultimo = evento
        return m

    def test_manda_el_semanal_y_si_no_dice_nada_el_mensual(self):
        ruptura_alcista = Evento("W1", "ruptura", +1, 0, 0)
        rango_bajista = Evento("MN", "rango", -1, 0, 0, objetivo=1, barrido=2)
        self.assertEqual(sesgo_de_fondo(self._marco(ruptura_alcista), self._marco(None)), +1)
        self.assertEqual(sesgo_de_fondo(self._marco(None), self._marco(rango_bajista)), -1)
        self.assertEqual(sesgo_de_fondo(self._marco(ruptura_alcista), self._marco(rango_bajista)), 0)  # se contradicen
        rango_bajista.estado = "completado"
        self.assertEqual(sesgo_de_fondo(self._marco(None), self._marco(rango_bajista)), 0)


if __name__ == "__main__":
    unittest.main()
