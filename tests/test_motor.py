import unittest
from dataclasses import replace
from datetime import date

from crt.marcos import Marco, Setup
from crt.mercados import Mercado
from crt.motor import Ajustes, Operacion, _cabe, _niveles, _revisar_salida, probar, probar_cartera, sesgo_de_fondo
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
# Velas de 4H de historia que suben y bajan 1 punto (sin order blocks ni rangos), para tener tamaño medio.
HISTORIA = [("2025-03-02 21:00", 104), ("2025-03-03 01:00", 105), ("2025-03-03 05:00", 104), ("2025-03-03 09:00", 105), ("2025-03-03 13:00", 104), ("2025-03-03 17:00", 105)]


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

    def test_un_rango_viejo_de_4h_no_tapa_el_verde_anticipado_del_diario(self):
        # El martes, el 4H de las 5 forma un rango alcista (barrido 97) ANTES de que el diario barra el 95 del
        # lunes. La vela de 4H de las 9 baja a 94 y el 1H forma otro rango alcista: el 4H se está formando otra
        # vez al alza después del barrido del diario, y eso pone el diario en verde (antes salía ámbar).
        lunes = [("2025-03-02 18:00", 105), ("2025-03-03 03:00", 115), ("2025-03-03 10:00", 95), ("2025-03-03 17:00", 104)]
        martes = [
            ("2025-03-03 21:00", 104), ("2025-03-04 01:00", 106), ("2025-03-04 02:00", 110), ("2025-03-04 04:00", 100),
            ("2025-03-04 05:00", 105), ("2025-03-04 06:00", 103), ("2025-03-04 07:00", 101), ("2025-03-04 08:00", 97),
            ("2025-03-04 09:00", 103), ("2025-03-04 10:00", 96), ("2025-03-04 10:30", 94), ("2025-03-04 11:00", 98),
            ("2025-03-04 11:15", 97.6), ("2025-03-04 11:30", 99), ("2025-03-04 12:30", 108),
        ]  # fmt: skip
        res = probar(camino(lunes + martes), SIN_COSTES, Ajustes(sesgo_fijo=+1, comprobar_objetivo_diario=False))
        senales = {s.hora: (s.decision, s.diario) for s in res.senales}
        self.assertEqual(senales[ny("2025-03-04 11:30")], ("entrada", "verde"))


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

    def test_no_anticipa_si_la_vela_de_4h_ya_tomo_el_otro_extremo(self):
        # Lo mismo, pero antes de barrer el 100 la vela de las 5 sube a 111 y toma el máximo de la
        # anterior (110): ya no puede cerrar como rango alcista, así que el 4H no se pone en verde.
        puntos = HASTA_LAS_9[:5] + [("2025-03-04 05:30", 111)] + self.PUNTOS[5:]
        self.assertEqual(probar(camino(puntos), SIN_COSTES, SOLO_4H).operaciones, [])


SUBE = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125)]


class Banderas(unittest.TestCase):
    def test_apunta_las_banderas_rojas_y_la_nota(self):
        # A las 9:30 la vela de 1H de las 9 ya ha pasado el máximo de la de las 8 (103), la vela de 3H de
        # las 5 cerró a las 8:00 por debajo de la anterior (ruptura bajista) y es justo antes de la apertura.
        s = probar(camino(SUBE), SIN_COSTES, SOLO_4H).senales[0]
        self.assertEqual(s.banderas, ("el 1H está tomando máximos", "el 3H va en contra", "justo antes de la apertura"))
        self.assertEqual((s.h3, s.h1, s.nota), ("rojo", "ambar", "C"))

    def test_solo_situaciones_sin_banderas(self):
        res = probar(camino(SUBE), SIN_COSTES, replace(SOLO_4H, sin_banderas=True))
        self.assertEqual(res.operaciones, [])
        self.assertEqual(res.descartadas["situación con banderas rojas"], 1)


class ExigirElMarcoMenor(unittest.TestCase):
    def test_el_1h(self):
        # A las 9:30 el 1H está en ámbar: no está a favor, pero tampoco en contra.
        res = probar(camino(SUBE), SIN_COSTES, replace(SOLO_4H, exigir_1h="verde"))
        self.assertEqual(res.descartadas["el 1H no acompaña"], 1)
        self.assertEqual(len(probar(camino(SUBE), SIN_COSTES, replace(SOLO_4H, exigir_1h="no_rojo")).operaciones), 1)

    def test_el_3h(self):
        res = probar(camino(SUBE), SIN_COSTES, replace(SOLO_4H, exigir_3h="verde"))
        self.assertEqual(res.descartadas["el 3H no acompaña"], 1)


class SalidaPor1H(unittest.TestCase):
    # Compra a 104 con el stop en 97 (1 R = 7). La vela de 1H de las 11 sube a 111 y cierra a 108,
    # dentro de la de las 10 (106-110): rango bajista de 1H a las 12:00. Después cae a 95.
    GANANDO = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [
        ("2025-03-04 10:00", 106),
        ("2025-03-04 11:00", 110),
        ("2025-03-04 11:30", 111),
        ("2025-03-04 12:00", 108),
        ("2025-03-04 13:00", 95),
    ]
    # La vela de 1H de las 9 sube a 106 y cierra a 102,8, dentro de la de las 8 (97-103): rango
    # bajista de 1H a las 10:00, con la operación perdiendo.
    PERDIENDO = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 09:45", 106), ("2025-03-04 10:00", 102.8), ("2025-03-04 11:00", 95)]

    def _op(self, puntos, salida):
        return probar(camino(puntos), SIN_COSTES, replace(SOLO_4H, salida_1h=salida)).operaciones[0]

    def test_sin_la_regla_acaba_en_stop(self):
        self.assertEqual(self._op(self.GANANDO, None).resultado, "SL")

    def test_salir_al_formarse_el_rango_en_contra(self):
        op = self._op(self.GANANDO, "salir")
        self.assertEqual((op.resultado, op.hora_salida), ("Salida por 1H", ny("2025-03-04 12:00")))
        self.assertAlmostEqual(op.r, 4 / 7)

    def test_stop_a_la_entrada_si_va_ganando(self):
        op = self._op(self.GANANDO, "entrada")
        self.assertEqual((op.resultado, round(op.r, 6)), ("BE", 0.0))

    def test_si_va_perdiendo_sale(self):
        op = self._op(self.PERDIENDO, "entrada")
        self.assertEqual((op.resultado, op.hora_salida), ("Salida por 1H", ny("2025-03-04 10:00")))
        self.assertAlmostEqual(op.r, -1.2 / 7)


class ZonaDePeligro(unittest.TestCase):
    """Vídeo de los 6.000 $: ganando, con máximos nuevos en 4H y en 1H y un barrido en contra en M15, se sale."""

    def _barras(self):
        # Compra a 104 (stop 97). A las 10:30 el precio está en 109: la vela de 4H de las 9 ya supera el máximo
        # de la de las 5 (105) y la de 1H de las 10 el de la de las 9 (106). La vela de M15 de las 10:30 sube a
        # 110,5 y vuelve a cerrar dentro de la anterior (108,8): barrido bajista. Después cae a 95.
        barras = camino(HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 10:00", 106), ("2025-03-04 10:30", 109)])
        barras.append(Vela(ny("2025-03-04 10:30"), 109, 110.5, 108.6, 108.8))
        barras += camino([("2025-03-04 10:45", 108.8), ("2025-03-04 11:30", 95), ("2025-03-04 12:00", 96)])
        for k, b in enumerate(barras):
            b.i_inicio = b.i_fin = k
        return barras

    def test_sin_la_regla_acaba_en_stop(self):
        self.assertEqual(probar(self._barras(), SIN_COSTES, SOLO_4H).operaciones[0].resultado, "SL")

    def test_sale_en_la_zona_de_peligro(self):
        op = probar(self._barras(), SIN_COSTES, replace(SOLO_4H, salida_peligro=True)).operaciones[0]
        self.assertEqual((op.resultado, op.hora_salida), ("Zona de peligro", ny("2025-03-04 10:45")))
        self.assertAlmostEqual(op.r, 4.8 / 7)


class VelaDiariaExpansiva(unittest.TestCase):
    """Vídeo de los 6.000 $: tras una vela diaria expansiva a favor, el objetivo es su máximo y no hace falta
    esperar a otro rango diario."""

    # El lunes va de 80 a 90 y el martes cierra en 130, por encima del máximo del lunes. El miércoles no barre
    # el mínimo del martes, así que no hay rango diario, pero sí el rango de 4H y el order block de siempre.
    PUNTOS = [("2025-03-02 18:00", 80), ("2025-03-03 17:00", 90), ("2025-03-04 17:00", 130)] + [
        (t.replace("2025-03-04", "2025-03-05").replace("2025-03-03", "2025-03-04"), p) for t, p in HASTA_LAS_9 + ORDER_BLOCK_9_30
    ] + [("2025-03-05 11:00", 125), ("2025-03-05 13:00", 125)]

    def _res(self, diario):
        return probar(camino(self.PUNTOS), SIN_COSTES, Ajustes(sesgo_fijo=+1, diario=diario))

    def test_con_el_diario_obligatorio_no_entra(self):
        self.assertEqual(self._res("verde").descartadas["el diario no está a favor"], 1)

    def test_tras_la_vela_expansiva_entra(self):
        ops = self._res("expansiva").operaciones
        self.assertEqual([(o.hora_entrada, o.resultado) for o in ops], [(ny("2025-03-05 09:30"), "TP")])

    def test_sin_vela_expansiva_no_vale(self):
        res = probar(camino(SUBE), SIN_COSTES, Ajustes(sesgo_fijo=+1, diario="expansiva"))
        self.assertEqual(res.descartadas["el diario no está a favor"], 1)


class LoteDeTreceVideos(unittest.TestCase):
    """Reglas candidatas del lote de 13 vídeos del canal."""

    def test_no_perseguir_espera_un_order_block_mas_cerca_del_barrido(self):
        # Con velas de 4H pequeñas de historia, la entrada de las 9:30 (stop de 7) queda lejos del barrido. El
        # precio vuelve a 98,8 y a las 10:45 hay otro order block con el stop a 2,5: esa sí.
        puntos = HISTORIA + HASTA_LAS_9 + ORDER_BLOCK_9_30 + [
            ("2025-03-04 09:45", 102),
            ("2025-03-04 10:15", 99),
            ("2025-03-04 10:30", 98.8),
            ("2025-03-04 10:45", 99.5),
            ("2025-03-04 12:00", 106),
        ]
        sin = probar(camino(puntos), SIN_COSTES, SOLO_4H)
        self.assertEqual([(s.hora, s.decision) for s in sin.senales], [(ny("2025-03-04 09:30"), "entrada")])
        res = probar(camino(puntos), SIN_COSTES, replace(SOLO_4H, no_perseguir=True))
        self.assertEqual(
            [(s.hora, s.decision) for s in res.senales],
            [(ny("2025-03-04 09:30"), "la entrada queda lejos del barrido"), (ny("2025-03-04 10:45"), "entrada")],
        )
        self.assertEqual([(o.resultado, round(o.r, 6)) for o in res.operaciones], [("TP", 2.0)])

    def test_comprar_solo_por_debajo_de_la_apertura_del_dia(self):
        # El día abre a las 17:00 del lunes en 100 y la compra de las 9:30 es a 104.
        puntos = [("2025-03-03 17:00", 100)] + SUBE
        s = probar(camino(puntos), SIN_COSTES, SOLO_4H).senales[0]
        self.assertIn("compra por encima de la apertura del día", s.banderas)
        res = probar(camino(puntos), SIN_COSTES, replace(SOLO_4H, apertura_del_dia=True))
        self.assertEqual(res.descartadas["al otro lado de la apertura del día"], 1)

    def test_no_entrar_antes_de_una_noticia_fuerte(self):
        ajustes = replace(SOLO_4H, antes_de_noticias=True)
        antes = probar(camino(SUBE), SIN_COSTES, ajustes, {date(2025, 3, 4): ["10:00 ISM de servicios"]})
        self.assertEqual(antes.descartadas["antes de una noticia fuerte"], 1)
        despues = probar(camino(SUBE), SIN_COSTES, ajustes, {date(2025, 3, 4): ["08:30 Nóminas no agrícolas"]})
        self.assertEqual(despues.senales[0].decision, "entrada")

    def test_cerrar_al_final_del_dia(self):
        puntos = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 17:00", 105), ("2025-03-04 18:00", 106)]
        self.assertEqual(probar(camino(puntos), SIN_COSTES, SOLO_4H).operaciones, [])  # sigue abierta
        op = probar(camino(puntos), SIN_COSTES, replace(SOLO_4H, cierre_diario=True)).operaciones[0]
        self.assertEqual((op.resultado, op.hora_salida), ("Cierre del día", ny("2025-03-04 17:00")))
        self.assertAlmostEqual(op.r, 1 / 7)

    def test_salida_por_tiempo(self):
        # Compra a 104 (stop 97). La vela de 4H de las 9 llega a 110; la de las 13, que abre después de la
        # entrada, supera ese máximo a las 13:45 (110,25): salida por tiempo. Sin la regla, acaba en stop.
        puntos = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [
            ("2025-03-04 11:00", 110),
            ("2025-03-04 13:00", 108),
            ("2025-03-04 14:00", 111),
            ("2025-03-04 16:00", 95),
        ]
        self.assertEqual(probar(camino(puntos), SIN_COSTES, SOLO_4H).operaciones[0].resultado, "SL")
        op = probar(camino(puntos), SIN_COSTES, replace(SOLO_4H, salida_por_tiempo=True)).operaciones[0]
        self.assertEqual((op.resultado, op.hora_salida), ("Salida por tiempo", ny("2025-03-04 13:45")))
        self.assertAlmostEqual(op.r, 6.25 / 7)

    def test_stop_a_la_entrada_antes_de_la_vela_de_las_9(self):
        # La compra anticipada de las 8:30 (101,6; stop 98,5) va ganando a las 9:00 y después cae a 97.
        puntos = AnticipoCon1H.PUNTOS[:-2] + [("2025-03-04 09:00", 103), ("2025-03-04 10:00", 97)]
        self.assertEqual(probar(camino(puntos), SIN_COSTES, SOLO_4H).operaciones[0].resultado, "SL")
        op = probar(camino(puntos), SIN_COSTES, replace(SOLO_4H, be_antes_de_las_9=True)).operaciones[0]
        self.assertEqual((op.resultado, round(op.r, 6)), ("BE", 0.0))

    def test_el_tp_tiene_que_caber_antes_del_objetivo_del_4h(self):
        ajustes = replace(SOLO_4H, comprobar_objetivo_4h=True)
        self.assertEqual(probar(camino(SUBE), SIN_COSTES, ajustes).senales[0].decision, "el TP no cabe antes del objetivo del 4H")
        lejos = [(t, 120 if t == "2025-03-04 02:00" else p) for t, p in HASTA_LAS_9] + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125)]
        self.assertEqual(probar(camino(lejos), SIN_COSTES, ajustes).senales[0].decision, "entrada")

    def test_sin_sesgo(self):
        en_contra = replace(SOLO_4H, sesgo_fijo=-1)
        self.assertEqual(probar(camino(SUBE), SIN_COSTES, en_contra).senales[0].decision, "sin sesgo a favor")
        self.assertEqual(probar(camino(SUBE), SIN_COSTES, replace(en_contra, ignorar_sesgo=True)).senales[0].decision, "entrada")

    def test_no_entrar_con_el_diario_o_el_4h_tomando_a_favor(self):
        res = probar(camino(HISTORIA + SUBE), SIN_COSTES, replace(SOLO_4H, vetar_tomando=True))
        self.assertIn("el diario está tomando máximos", res.senales[0].banderas)
        self.assertEqual(res.descartadas["situación con banderas rojas"], 1)

    def test_dejar_correr_hasta_el_objetivo_del_4h(self):
        lejos = [(t, 120 if t == "2025-03-04 02:00" else p) for t, p in HASTA_LAS_9] + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125)]
        ajustes = replace(SOLO_4H, tp_hasta_objetivo_4h=True)
        self.assertEqual(probar(camino(lejos), SIN_COSTES, ajustes).operaciones[0].tp, 120)  # más lejos que 1 a 2
        self.assertEqual(probar(camino(SUBE), SIN_COSTES, ajustes).operaciones[0].tp, 118)  # el de 110 queda antes


class NivelesConCostes(unittest.TestCase):
    # Con diferencial 0,5 y colchón 1: se compra al precio de compra y las ventas se cierran comprando, así que
    # la compra y la venta espejo arriesgan lo mismo.
    MERCADO = Mercado("prueba", diferencial=0.5, colchon=1.0, decimales=1)

    def test_compra_y_venta_espejo_arriesgan_lo_mismo(self):
        compra = Setup(("c",), +1, barrido=97, objetivo=130, i_inicio=0, via="cierre", escenario="otro")
        venta = Setup(("v",), -1, barrido=103, objetivo=70, i_inicio=0, via="cierre", escenario="otro")
        self.assertEqual(_niveles(+1, 104, compra, self.MERCADO, 2.0), (104.5, 96.0, 8.5, 121.5))
        self.assertEqual(_niveles(-1, 96, venta, self.MERCADO, 2.0), (96, 104.5, 8.5, 79.0))

    def test_stop_demasiado_corto_y_precio_pasado_del_barrido(self):
        caro = Mercado("prueba", diferencial=1.0, colchon=0.5, decimales=1)
        compra = Setup(("c",), +1, barrido=103, objetivo=130, i_inicio=0, via="cierre", escenario="otro")
        self.assertEqual(_niveles(+1, 104, compra, caro, 2.0), "stop demasiado corto")  # 105 − 102,5 = 2,5 < 3 diferenciales
        self.assertEqual(_niveles(+1, 103, compra, caro, 2.0), "el precio ya pasó el barrido")

    def test_en_ventas_el_objetivo_se_compara_con_el_precio_de_compra(self):
        self.assertTrue(_cabe(-1, 79.0, 78.5, self.MERCADO))  # 79 ≥ 78,5 + 0,5
        self.assertFalse(_cabe(-1, 78.9, 78.5, self.MERCADO))


class TpEnElObjetivoDe4H(unittest.TestCase):
    def test_el_tp_va_al_objetivo_del_rango(self):
        # La vela 1 sube hasta 120: el objetivo del rango de 4H está a 16 puntos de la entrada (2,3 R).
        puntos = [(t, 120 if t == "2025-03-04 02:00" else p) for t, p in HASTA_LAS_9] + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125)]
        op = probar(camino(puntos), SIN_COSTES, replace(SOLO_4H, tp_objetivo_4h=True)).operaciones[0]
        self.assertEqual((op.tp, op.resultado), (120, "TP"))
        self.assertAlmostEqual(op.r, 16 / 7)

    def test_no_entra_si_el_objetivo_esta_a_menos_de_1_r(self):
        # El objetivo (110) está a 6 puntos y 1 R son 7.
        res = probar(camino(SUBE), SIN_COSTES, replace(SOLO_4H, tp_objetivo_4h=True))
        self.assertEqual(res.operaciones, [])
        self.assertEqual(res.descartadas["el objetivo del 4H está a menos de 1 R"], 1)


class VolverAEntrarTrasUnStop(unittest.TestCase):
    # La compra de las 9:30 acaba en stop (97). La vela de 4H de las 9 barre el mínimo de la de las 5
    # y en 1H la vela de las 11 barre el mínimo de la de las 10 y cierra dentro: se está formando otro
    # rango alcista de 4H. Order block a las 12:30 y segunda compra («me saca, reacciona, vuelve a
    # hacer un rango de 4H, un order block… y vuelvo a entrar», vídeo de los stops).
    PUNTOS = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [
        ("2025-03-04 10:00", 100),
        ("2025-03-04 10:30", 96),
        ("2025-03-04 11:00", 98),
        ("2025-03-04 11:30", 95.5),
        ("2025-03-04 12:00", 99),
        ("2025-03-04 12:15", 98.7),
        ("2025-03-04 12:30", 99.8),
        ("2025-03-04 14:00", 110),
    ]

    def _res(self, **cambios):
        return probar(camino(self.PUNTOS), SIN_COSTES, replace(SOLO_4H, **cambios))

    def test_vuelve_a_entrar_con_la_idea_nueva(self):
        ops = self._res().operaciones
        self.assertEqual(
            [(o.hora_entrada, o.via, o.resultado) for o in ops],
            [(ny("2025-03-04 09:30"), "cierre", "SL"), (ny("2025-03-04 12:30"), "anticipo", "TP")],
        )
        self.assertAlmostEqual(ops[1].stop, 95.5)

    def test_tope_de_perdida_del_dia(self):
        res = self._res(perdida_max_dia_r=1.0)
        self.assertEqual(len(res.operaciones), 1)
        self.assertEqual(res.descartadas["tope de pérdida del día"], 1)

    def test_pausa_tras_una_racha_de_stops(self):
        res = self._res(pausa_tras_stops=1)
        self.assertEqual(len(res.operaciones), 1)
        self.assertEqual(res.descartadas["pausa tras una racha de stops"], 1)


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


class Cartera(unittest.TestCase):
    # «a» compra a las 9:30 y toca el stop a las 9:45; «b» compra a las 10:30 y llega al TP.
    PIERDE = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 09:45", 96), ("2025-03-04 13:00", 96)]
    GANA_TARDE = HASTA_LAS_9 + [("2025-03-04 10:15", 102.5), ("2025-03-04 10:30", 104), ("2025-03-04 12:00", 125), ("2025-03-04 13:00", 125)]

    def _juntos(self, ajustes):
        return probar_cartera({"a": (camino(self.PIERDE), SIN_COSTES), "b": (camino(self.GANA_TARDE), SIN_COSTES)}, ajustes)

    def test_sin_llegar_al_tope_cada_mercado_sale_igual_que_solo(self):
        solo = probar(camino(self.GANA_TARDE), SIN_COSTES, SOLO_4H)
        juntos = self._juntos(SOLO_4H)
        self.assertEqual([(o.hora_entrada, o.resultado) for o in juntos["b"].operaciones], [(ny("2025-03-04 10:30"), "TP")])
        self.assertEqual([(o.hora_entrada, o.resultado) for o in solo.operaciones], [(ny("2025-03-04 10:30"), "TP")])
        self.assertEqual([o.resultado for o in juntos["a"].operaciones], ["SL"])

    def test_el_tope_del_dia_suma_lo_de_todos_los_mercados(self):
        juntos = self._juntos(replace(SOLO_4H, perdida_max_dia_r=1.0))
        self.assertEqual(juntos["b"].operaciones, [])
        self.assertEqual(juntos["b"].descartadas["tope de pérdida del día"], 1)

    def test_tope_cero_es_sin_tope_como_en_mt5(self):
        self.assertEqual(len(probar(camino(self.GANA_TARDE), SIN_COSTES, replace(SOLO_4H, perdida_max_dia_r=0.0)).operaciones), 1)


if __name__ == "__main__":
    unittest.main()
