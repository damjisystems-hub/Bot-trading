"""El indicador de TradingView tiene que decir lo mismo que el bot: mismos textos, mismos valores por defecto,
mismos costes y los mismos casos del examen. Y los scripts tienen que estar generados con la plantilla de ahora."""

import os
import re
import unittest
from dataclasses import fields

from crt import motor
from crt.casos import leer_casos
from crt.mercados import MERCADOS
from tradingview import generar

CARPETA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tradingview")


def _leer(nombre: str) -> str:
    with open(os.path.join(CARPETA, nombre), encoding="utf-8") as f:
        return f.read()


class Generados(unittest.TestCase):
    def test_los_scripts_estan_al_dia_con_la_plantilla(self):
        for tipo, nombre in generar.ARCHIVOS.items():
            with self.subTest(nombre=nombre):
                self.assertEqual(_leer(nombre), generar.construir(tipo), "volved a ejecutar: python3 tradingview/generar.py")

    def test_el_indicador_no_opera_y_la_estrategia_si(self):
        indicador, estrategia = _leer("CRT_indicador.pine"), _leer("CRT_estrategia.pine")
        self.assertIn("indicator(", indicador)
        self.assertNotIn("strategy.", indicador)
        self.assertIn("strategy(", estrategia)
        self.assertIn("strategy.entry(", estrategia)
        self.assertNotIn("alertcondition(", estrategia)
        for texto in (indicador, estrategia):
            self.assertTrue(texto.startswith("//@version=5\n"))
            self.assertNotIn("//@", texto.replace("//@version=5", ""))  # no queda ninguna marca de la plantilla


class MismasReglas(unittest.TestCase):
    def setUp(self):
        self.pine = _leer("plantilla.pine")

    def test_mismas_banderas_rojas(self):
        for bandera in motor.BANDERAS:
            with self.subTest(bandera=bandera):
                self.assertIn(f'"{bandera}"', self.pine)

    def test_los_motivos_son_los_de_la_memoria(self):
        motivos = set(re.findall(r'decision := "([^"]+)"', self.pine)) | set(re.findall(r'motivo := "([^"]+)"', self.pine))
        self.assertLessEqual(motivos, set(motor.DECISIONES))
        for motivo in (motor.SIN_SESGO, motor.DIARIO_EN_CONTRA, motor.YA_ABIERTA, motor.TOPE_DE_PERDIDA, motor.TOPE_DEL_DIA,
                       motor.PASO_EL_BARRIDO, motor.STOP_CORTO, motor.TP_NO_CABE, motor.ENTRADA):  # fmt: skip
            self.assertIn(motivo, motivos)

    def test_los_valores_por_defecto_son_los_decididos(self):
        a = motor.Ajustes()
        pine = self.pine
        self.assertIn(f'input.float({a.ratio}, "TP', pine)
        self.assertIn(f"input.int({a.espera_apertura_min}, ", pine)
        self.assertIn(f'input.string("{a.desde:%H:%M}", "Entradas desde', pine)
        self.assertIn(f'input.string("{a.hasta:%H:%M}", "Entradas hasta', pine)
        self.assertIn(f'input.int({a.max_operaciones_dia}, "Máximo de operaciones', pine)
        self.assertIn(f'input.float({a.perdida_max_dia_r}, "Tope de pérdida', pine)
        self.assertIn(f'input.int({a.inicio_4h}, "Las velas de 4H', pine)
        self.assertIn(f'input.bool({str(a.comprobar_objetivo_diario).lower()}, "No entrar si el TP', pine)
        self.assertIn(f"riesgo < {motor.STOP_MINIMO_EN_DIFERENCIALES} * dif", pine)
        # Las reglas candidatas que tiene, apagadas como en el bot.
        for campo in ("anticipo_sin_1h", "sin_veto_mensual", "ignorar_sesgo"):
            self.assertIs(getattr(a, campo), False)
        self.assertEqual(re.findall(r"input\.bool\((\w+), \"(?:4H anticipado|Sesgo: manda|Modelo del backtest)", pine), ["false"] * 3)

    def test_las_candidatas_que_tiene_existen_en_el_bot(self):
        nombres = {f.name for f in fields(motor.Ajustes)}
        self.assertLessEqual({"anticipo_sin_1h", "sin_veto_mensual", "ignorar_sesgo"}, nombres)


class MismosDatos(unittest.TestCase):
    def test_mismos_costes_por_mercado(self):
        texto = generar.mercados()
        for clave, m in MERCADOS.items():
            with self.subTest(mercado=clave):
                self.assertIn(f'mercado == "{clave}" ? {generar._numero(m.diferencial)}', texto)
                self.assertIn(f'mercado == "{clave}" ? {generar._numero(m.colchon)}', texto)
                self.assertAlmostEqual(float(generar._numero(m.diferencial)), m.diferencial)
        self.assertNotRegex(texto, r"\de-?\d")  # sin notación científica, que Pine podría no entender

    def test_estan_todos_los_casos_con_fecha(self):
        texto = generar.casos(os.path.join(os.path.dirname(CARPETA), "casos", "casos.csv"))
        con_fecha = [c for c in leer_casos(os.path.join(os.path.dirname(CARPETA), "casos", "casos.csv")) if c.desde and c.hasta]
        self.assertGreater(len(con_fecha), 0)
        for c in con_fecha:
            with self.subTest(caso=c.id):
                self.assertIn(f'"{c.id}"', texto)
                self.assertIn(f"timestamp(NY, {c.desde.year}, {c.desde.month}, {c.desde.day}, {c.desde.hour}, {c.desde.minute})", texto)


if __name__ == "__main__":
    unittest.main()


class DecideIgualQueElBot(unittest.TestCase):
    """El indicador, traducido a Python (tradingview/espejo.py), sobre precios inventados: mismas entradas, mismos
    niveles, mismos resultados y mismas señales descartadas que el bot."""

    @staticmethod
    def _camino(semilla: int, dias: int = 120) -> list:
        import random
        from datetime import datetime, timedelta

        from crt.velas import Vela, dia_de_trading

        rnd, barras, p, t = random.Random(semilla), [], 100.0, datetime(2024, 1, 7, 17, 0)
        while len(barras) < dias * 96:
            if dia_de_trading(t).weekday() < 5:
                a, b = p, p + rnd.gauss(0, 0.12)
                barras.append(Vela(t, a, max(a, b) + abs(rnd.gauss(0, 0.05)), min(a, b) - abs(rnd.gauss(0, 0.05)), b, len(barras), len(barras)))
                p = b
            t += timedelta(minutes=15)
        return barras

    def test_mismas_entradas_y_mismos_motivos(self):
        from crt.mercados import Mercado
        from tradingview.espejo import Espejo, V

        mercado = Mercado("AZAR", diferencial=0.02, colchon=0.03, decimales=2)
        barras = self._camino(7)
        for ajustes, extra in ((motor.Ajustes(), {}), (motor.Ajustes(anticipo_sin_1h=True, sin_veto_mensual=True), {"sin1h": True, "sinVeto": True})):
            with self.subTest(ajustes=extra):
                bot = motor.probar(barras, mercado, ajustes)
                espejo = Espejo(mercado.diferencial, mercado.colchon, **extra)
                for b in barras:
                    espejo.paso(V(b.inicio, b.apertura, b.maximo, b.minimo, b.cierre, b.i_inicio, b.i_fin))
                self.assertGreater(len(bot.operaciones), 0)
                self.assertEqual(
                    [(o.hora_entrada, o.direccion, round(o.entrada, 6), round(o.stop, 6), round(o.tp, 6), o.resultado, round(o.r, 6)) for o in bot.operaciones],
                    [(o["t"], o["dir"], round(o["entrada"], 6), round(o["stop"], 6), round(o["tp"], 6), o["resultado"], round(o["r"], 6)) for o in espejo.ops],
                )
                self.assertEqual([(s.hora, s.direccion, s.decision) for s in bot.senales], espejo.senales)
