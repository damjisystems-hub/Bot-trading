import os
import tempfile
import unittest
from datetime import date

from crt import aprendizaje, casos, laboratorio, memoria
from crt.mercados import MERCADOS
from crt.motor import Ajustes, probar
from crt.noticias import leer_noticias
from tests.ayuda import SIN_COSTES, camino, ny
from tests.test_motor import HASTA_LAS_9, HISTORIA, ORDER_BLOCK_9_30, SOLO_4H

SUBE_AL_TP = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125), ("2025-03-04 13:00", 125)]


class Memoria(unittest.TestCase):
    def test_apunta_la_entrada_con_su_contexto_y_su_resultado(self):
        res = probar(camino(HISTORIA + SUBE_AL_TP), SIN_COSTES, SOLO_4H)
        entradas = [s for s in res.senales if s.decision == "entrada"]
        self.assertEqual(len(entradas), 1)
        s = entradas[0]
        self.assertEqual((s.hora, s.sesion, s.via_4h, s.sesgo_semanal), (ny("2025-03-04 09:30"), "Londres", "cierre", 0))
        self.assertIsNotNone(s.vela1_rel)
        self.assertGreaterEqual(s.operacion.mfe_r, 2.0)
        fila = memoria.filas(res)[0]
        self.assertEqual((fila["direccion"], fila["decision"], fila["tomada"], fila["resultado"], fila["r"]), ("compra", "entrada", "si", "TP", "2.00"))
        self.assertEqual(list(fila), memoria.COLUMNAS)
        self.assertEqual((fila["h3"], fila["h1"], fila["nota"]), ("rojo", "ambar", "C"))
        self.assertIn("justo antes de la apertura", fila["banderas"].split(" | "))

    def test_la_senal_descartada_se_sigue_como_fantasma(self):
        # Con el diario obligatorio no entra, pero apunta por qué y qué habría pasado.
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, Ajustes(sesgo_fijo=+1))
        self.assertEqual(res.operaciones, [])
        s = next(s for s in res.senales if s.direccion > 0)
        self.assertEqual(s.decision, "el diario no está a favor")
        self.assertFalse(s.operacion.tomada)
        self.assertEqual((s.operacion.resultado, round(s.operacion.r, 6)), ("TP", 2.0))
        self.assertEqual(res.descartadas["el diario no está a favor"], 1)

    def test_guardar_y_leer(self):
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, SOLO_4H)
        ruta = os.path.join(tempfile.mkdtemp(), "memoria.csv")
        memoria.guardar(ruta, memoria.filas(res))
        self.assertEqual(memoria.leer(ruta), memoria.filas(res))


class ReglasCandidatas(unittest.TestCase):
    def test_stop_a_la_entrada_al_llegar_a_1_r(self):
        # Compra a 104 con stop en 97 (1 R = 7): sube a 111,5 (+1,07 R) y luego cae a 95.
        puntos = HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 10:30", 111.5), ("2025-03-04 12:00", 95)]
        sin = probar(camino(puntos), SIN_COSTES, SOLO_4H).operaciones[0]
        con = probar(camino(puntos), SIN_COSTES, Ajustes(sesgo_fijo=+1, diario="ignorar", stop_a_entrada_en_r=1.0)).operaciones[0]
        self.assertEqual((sin.resultado, round(sin.r, 6)), ("SL", -1.0))
        self.assertEqual((con.resultado, round(con.r, 6)), ("BE", 0.0))

    def test_vela_1_minima(self):
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, Ajustes(sesgo_fijo=+1, diario="ignorar", vela1_minima=50))
        self.assertEqual(res.operaciones, [])
        self.assertEqual(res.descartadas["vela 1 pequeña"], 1)

    def test_escenarios_permitidos(self):
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, Ajustes(sesgo_fijo=+1, diario="ignorar", escenarios=("1", "2")))
        self.assertEqual(res.descartadas["escenario no permitido"], 1)

    def test_dias_de_noticias(self):
        noticias = {date(2025, 3, 4): ["8:30 Prueba"]}
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, Ajustes(sesgo_fijo=+1, diario="ignorar", sin_noticias=True), noticias)
        self.assertEqual(res.operaciones, [])
        self.assertEqual(res.descartadas["día de noticias fuertes"], 1)
        con = probar(camino(SUBE_AL_TP), SIN_COSTES, SOLO_4H, noticias)
        self.assertEqual(con.senales[0].noticias, "8:30 Prueba")

    def test_leer_noticias(self):
        ruta = os.path.join(tempfile.mkdtemp(), "noticias.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("fecha,hora,moneda,evento,importancia\n2025-03-07,08:30,USD,Nóminas no agrícolas,alta\n2025-03-07,09:00,USD,Otra,media\n2025-03-06,08:15,EUR,BCE,alta\n")
        self.assertEqual(leer_noticias(ruta), {date(2025, 3, 7): ["08:30 Nóminas no agrícolas"]})
        self.assertEqual(len(leer_noticias(ruta, ("USD", "EUR"))), 2)

    def test_la_libra_mira_las_noticias_de_la_libra_y_del_dolar(self):
        ruta = os.path.join(tempfile.mkdtemp(), "noticias.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("fecha,hora,moneda,evento,importancia\n2025-03-07,08:30,USD,Nóminas,alta\n2025-03-06,07:00,GBP,Banco de Inglaterra,alta\n2025-03-06,08:15,EUR,BCE,alta\n")
        noticias = leer_noticias(ruta, MERCADOS["gbpusd"].monedas)
        self.assertEqual(noticias, {date(2025, 3, 7): ["08:30 Nóminas"], date(2025, 3, 6): ["07:00 Banco de Inglaterra"]})


class Laboratorio(unittest.TestCase):
    def test_veredictos(self):
        base = ({"n": 100, "media": 0.10}, {"n": 50, "media": 0.10})
        self.assertTrue(laboratorio.veredicto(base, ({"n": 80, "media": 0.2}, {"n": 40, "media": 0.15})).startswith("MEJORA"))
        self.assertTrue(laboratorio.veredicto(base, ({"n": 80, "media": 0.2}, {"n": 40, "media": 0.05})).startswith("dudosa"))
        self.assertEqual(laboratorio.veredicto(base, ({"n": 80, "media": 0.0}, {"n": 40, "media": 0.0})), "no mejora")
        self.assertEqual(laboratorio.veredicto(base, ({"n": 10, "media": 1.0}, {"n": 40, "media": 1.0})), "pocas operaciones para saberlo")

    def test_compara_todas_las_candidatas(self):
        barras = camino(SUBE_AL_TP)
        corte, base, pruebas = laboratorio.comprobar(barras, SIN_COSTES, SOLO_4H)
        sin_noticias = [c for _, c in laboratorio.CANDIDATAS if laboratorio.necesita_noticias(c)]
        self.assertEqual(len(pruebas), len(laboratorio.CANDIDATAS) - len(sin_noticias))  # sin noticias no se prueban esas
        self.assertIn("Laboratorio", laboratorio.texto(corte, base, pruebas, hay_noticias=False))


class InformeDeAprendizaje(unittest.TestCase):
    def test_saca_el_informe_de_la_memoria(self):
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, Ajustes(sesgo_fijo=+1))
        texto = aprendizaje.informe(memoria.filas(res))
        self.assertIn("el diario no está a favor", texto)
        self.assertIn("Lo que enseña la memoria", texto)

    def test_banderas_y_psicologia(self):
        texto = aprendizaje.informe(memoria.filas(probar(camino(SUBE_AL_TP), SIN_COSTES, SOLO_4H)))
        self.assertIn("Por bandera roja", texto)
        self.assertIn("el 3H va en contra", texto)
        self.assertIn("Psicología", texto)
        self.assertIn("Peor racha: 0 stops seguidos", texto)

    def test_la_racha_normal_de_stops(self):
        # Con un 35 % de acierto, en 200 operaciones es normal ver unos 10 stops seguidos.
        self.assertEqual(aprendizaje.racha_normal(200, 0.35), 10)
        self.assertEqual(aprendizaje.racha_normal(100, 0.5), 6)
        self.assertIsNone(aprendizaje.racha_normal(5, 0.5))

    def test_lee_memorias_sin_las_columnas_nuevas(self):
        filas = memoria.filas(probar(camino(SUBE_AL_TP), SIN_COSTES, SOLO_4H))
        for f in filas:
            for c in ("h3", "h1", "banderas", "nota"):
                del f[c]
        self.assertIn("Lo que enseña la memoria", aprendizaje.informe(filas))


class Examen(unittest.TestCase):
    def _casos(self, filas: str):
        ruta = os.path.join(tempfile.mkdtemp(), "casos.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("id,mercado,desde,hasta,esperado,fuente,nota\n" + filas)
        return casos.leer_casos(ruta)

    def test_aprueba_y_suspende_con_explicacion(self):
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, SOLO_4H)
        lista = self._casos(
            "a,nasdaq,2025-03-04 09:00,2025-03-04 13:00,compra,Prueba,Tenía que comprar\n"
            "b,nasdaq,2025-03-04 09:00,2025-03-04 13:00,venta,Prueba,Tenía que vender\n"
            "c,nasdaq,2025-03-04 02:00,2025-03-04 08:00,nada,Prueba,Nada antes de las 9\n"
            "d,nasdaq,,,compra,Prueba,Sin fecha\n"
            "e,nasdaq,2024-01-02 09:00,2024-01-02 13:00,compra,Prueba,Antes de los datos\n"
        )
        estados = [casos.examinar(c, res)[0] for c in lista]
        self.assertEqual(estados, ["bien", "mal", "bien", "falta la fecha", "sin datos"])
        self.assertIn("Compró a las 09:30", casos.examinar(lista[0], res)[1][0])
        self.assertIn("nota C (el 1H está tomando máximos, el 3H va en contra, justo antes de la apertura)", casos.examinar(lista[0], res)[1][0])
        self.assertIn("Resumen", casos.texto(lista, res))

    def test_el_archivo_de_casos_del_repositorio_se_lee_bien(self):
        lista = casos.leer_casos(os.path.join(os.path.dirname(__file__), "..", "casos", "casos.csv"))
        self.assertGreater(len(lista), 10)
        self.assertTrue(all(c.mercado in MERCADOS for c in lista))
        self.assertTrue(any(c.mercado == "gbpusd" for c in lista))


if __name__ == "__main__":
    unittest.main()
