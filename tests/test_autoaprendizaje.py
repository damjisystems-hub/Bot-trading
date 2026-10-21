import contextlib
import io
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date

import autoaprender
from autoaprender import mercado_del_archivo
from crt import autoaprendizaje, memoria
from crt.motor import ATRIBUTOS, REGLA_APRENDIDA, probar, vetada
from tests.ayuda import SIN_COSTES, camino
from tests.test_motor import HASTA_LAS_9, HISTORIA, ORDER_BLOCK_9_30, SOLO_4H

SUBE_AL_TP = HISTORIA + HASTA_LAS_9 + ORDER_BLOCK_9_30 + [("2025-03-04 11:00", 125), ("2025-03-04 13:00", 125)]


class Vetos(unittest.TestCase):
    def test_vetada(self):
        atributos = {"vela_4h": "vela de las 5", "bandera": ("el 3H va en contra",)}
        self.assertTrue(vetada(atributos, (("vela_4h", "vela de las 5"),)))
        self.assertTrue(vetada(atributos, (("bandera", "el 3H va en contra"),)))
        self.assertFalse(vetada(atributos, (("vela_4h", "vela de la 1 (Londres)"), ("bandera", "el 1H va en contra"))))

    def test_cada_texto_de_la_memoria_veta_esa_misma_situacion(self):
        # Lo que se aprende sale de la memoria y se aplica en el motor: los textos tienen que ser los mismos.
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, SOLO_4H)
        fila = next(f for f in memoria.filas(res) if f["decision"] == "entrada")
        valores = autoaprendizaje.valores(fila)
        for atributo in ATRIBUTOS:
            for valor in valores[atributo] if atributo == "bandera" else (valores[atributo],):
                if not valor:
                    continue
                with self.subTest(atributo=atributo, valor=valor):
                    vetado = probar(camino(SUBE_AL_TP), SIN_COSTES, replace(SOLO_4H, vetos=((atributo, valor),)))
                    self.assertEqual(vetado.operaciones, [])
                    self.assertEqual(vetado.descartadas[REGLA_APRENDIDA], 1)

    def test_un_veto_que_no_toca_la_situacion_no_cambia_nada(self):
        res = probar(camino(SUBE_AL_TP), SIN_COSTES, replace(SOLO_4H, vetos=(("dia_semana", "domingo"),)))
        self.assertEqual(len(res.operaciones), 1)


class PeoresSituaciones(unittest.TestCase):
    def _fila(self, hora, r, banderas="", sesion="Londres"):
        f = {c: "" for c in memoria.COLUMNAS}
        f.update(hora_ny=hora, r=str(r), tomada="si", banderas=banderas, sesion=sesion, direccion="compra", nota="B")
        return f

    def test_ordena_de_la_que_mas_pierde_a_la_que_mas_gana(self):
        filas = [self._fila("2025-03-04 03:00", -1, "el 1H va en contra") for _ in range(3)]
        filas += [self._fila("2025-03-04 10:30", 2, sesion="Tras la apertura") for _ in range(3)]
        lista = autoaprendizaje.peores(filas, minimo=3)
        self.assertEqual((lista[0].media, lista[-1].media), (-1.0, 2.0))
        self.assertIn(("bandera", "el 1H va en contra"), [(s.atributo, s.valor) for s in lista if s.media == -1.0])
        self.assertNotIn("", [s.valor for s in lista])

    def test_con_pocos_datos_no_aprende_nada(self):
        informe = autoaprendizaje.aprender(camino(SUBE_AL_TP), SIN_COSTES, SOLO_4H)
        self.assertEqual(informe.aprendidas, [])
        self.assertIn("No ha aprendido nada nuevo", autoaprendizaje.texto(informe))

    def test_mejora_clara_pide_operaciones_y_mas_que_el_error_tipico(self):
        base = {"n": 60, "media": 0.0, "varianza": 2.25}
        self.assertTrue(autoaprendizaje.mejora_clara(base, {"n": 40, "media": 0.8, "varianza": 2.25}))
        self.assertFalse(autoaprendizaje.mejora_clara(base, {"n": 40, "media": 0.1, "varianza": 2.25}))
        self.assertFalse(autoaprendizaje.mejora_clara(base, {"n": 10, "media": 2.0, "varianza": 0.0}))


class ArchivoDeReglas(unittest.TestCase):
    def test_escribir_cambia_solo_las_de_ese_mercado_y_dice_lo_desaprendido(self):
        ruta = os.path.join(tempfile.mkdtemp(), autoaprendizaje.ARCHIVO)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("# comentario\nPRUEBA;vela_4h;vela de las 5;2026-10-01;x\nOTRO;nota;C;2026-10-01;y\n")
        situacion = autoaprendizaje.Situacion("bandera", "el 3H va en contra", 40, -0.5, -20)
        tres = ({"n": 40, "media": -0.2}, {"n": 40, "media": -0.1}, {"n": 40, "media": -0.3})
        prueba = autoaprendizaje.Prueba(situacion, tres, tres, aprendida=True)
        informe = autoaprendizaje.Informe(SIN_COSTES, (None, None), tres, [situacion], [prueba], [prueba.veto])
        nuevas, desaprendidas = autoaprendizaje.escribir_reglas(ruta, informe, date(2026, 10, 21))
        self.assertEqual(nuevas, [("bandera", "el 3H va en contra")])
        self.assertEqual(desaprendidas, [("vela_4h", "vela de las 5")])
        self.assertEqual(autoaprendizaje.vetos_de(ruta, "PRUEBA"), (("bandera", "el 3H va en contra"),))
        self.assertEqual(autoaprendizaje.vetos_de(ruta, "OTRO"), (("nota", "C"),))  # las de otros mercados se quedan

    def test_mercado_de_los_archivos_que_exporta_mt5(self):
        self.assertEqual(mercado_del_archivo("barras_ny_EUR_USD.csv"), "eurusd")
        self.assertEqual(mercado_del_archivo("barras_ny_Oro_(XAU_USD).csv"), "oro")
        self.assertEqual(mercado_del_archivo("barras_ny_NASDAQ.csv"), "nasdaq")
        self.assertIsNone(mercado_del_archivo("barras_ny_US500.csv"))



class DeMT5AlAutoaprendizaje(unittest.TestCase):
    def test_lee_las_barras_que_exporta_mt5_y_deja_las_reglas_y_el_informe_en_su_carpeta(self):
        carpeta = tempfile.mkdtemp()
        # Como las escribe ExportarBarrasNY: separadas por tabuladores y ya en hora de Nueva York.
        with open(os.path.join(carpeta, "barras_ny_EUR_USD.csv"), "w", encoding="utf-8") as f:
            f.write("<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\r\n")
            for b in camino(SUBE_AL_TP):
                f.write(f"{b.inicio:%Y.%m.%d}\t{b.inicio:%H:%M:%S}\t{b.apertura}\t{b.maximo}\t{b.minimo}\t{b.cierre}\r\n")
        antes = sys.argv
        sys.argv = ["autoaprender.py", "--carpeta", carpeta]
        try:
            with contextlib.redirect_stdout(io.StringIO()) as salida:
                autoaprender.main()
        finally:
            sys.argv = antes
        self.assertIn("Autoaprendizaje · EUR/USD", salida.getvalue())
        self.assertTrue(os.path.exists(os.path.join(carpeta, autoaprendizaje.ARCHIVO)))
        self.assertTrue(os.path.exists(os.path.join(carpeta, "informe_autoaprendizaje.txt")))


if __name__ == "__main__":
    unittest.main()
