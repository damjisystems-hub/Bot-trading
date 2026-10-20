import os
import tempfile
import unittest
from datetime import date

from crt.velas import clave_y_fin, dia_de_trading, leer_csv
from tests.ayuda import ny


class HorarioDeLasVelas(unittest.TestCase):
    def test_las_velas_de_4h_empiezan_a_las_17_21_1_5_9_y_13(self):
        for inicio, ultima_barra in (
            ("2025-03-03 17:00", "2025-03-03 20:45"),
            ("2025-03-03 21:00", "2025-03-04 00:45"),
            ("2025-03-04 01:00", "2025-03-04 04:45"),
            ("2025-03-04 05:00", "2025-03-04 08:45"),
            ("2025-03-04 09:00", "2025-03-04 12:45"),
            ("2025-03-04 13:00", "2025-03-04 16:45"),
        ):
            clave, fin = clave_y_fin("H4", ny(inicio))
            self.assertEqual(clave_y_fin("H4", ny(ultima_barra))[0], clave)
            self.assertEqual(fin, ny(ultima_barra) + (ny("2025-01-01 00:15") - ny("2025-01-01 00:00")))

    def test_con_el_horario_de_futuros_las_velas_de_4h_empiezan_a_las_18_22_2_6_10_y_14(self):
        for inicio, ultima_barra in (
            ("2025-03-03 18:00", "2025-03-03 21:45"),
            ("2025-03-03 22:00", "2025-03-04 01:45"),
            ("2025-03-04 02:00", "2025-03-04 05:45"),
            ("2025-03-04 06:00", "2025-03-04 09:45"),
            ("2025-03-04 10:00", "2025-03-04 13:45"),
        ):
            clave, fin = clave_y_fin("H4", ny(inicio), inicio_4h=18)
            self.assertEqual(clave_y_fin("H4", ny(ultima_barra), inicio_4h=18)[0], clave)
            self.assertEqual(fin, ny(ultima_barra) + (ny("2025-01-01 00:15") - ny("2025-01-01 00:00")))
        # la vela de la apertura es «la de las 6», como en el vídeo de los 150.000 $
        self.assertEqual(clave_y_fin("H4", ny("2025-03-04 09:30"), inicio_4h=18)[1], ny("2025-03-04 10:00"))

    def test_las_velas_de_3h_empiezan_a_las_17_20_23_2_5_8_11_y_14(self):
        fines = [clave_y_fin("H3", ny(f"2025-03-04 {h:02d}:00"))[1].hour for h in (2, 5, 8, 11, 14)]
        self.assertEqual(fines, [5, 8, 11, 14, 17])
        self.assertEqual(clave_y_fin("H3", ny("2025-03-03 23:00"))[1], ny("2025-03-04 02:00"))
        self.assertEqual(clave_y_fin("H3", ny("2025-03-04 09:30"))[1], ny("2025-03-04 11:00"))  # «la de 3 horas de las 8»

    def test_la_vela_de_4h_de_las_9_no_incluye_las_8_45(self):
        self.assertNotEqual(clave_y_fin("H4", ny("2025-03-04 08:45"))[0], clave_y_fin("H4", ny("2025-03-04 09:00"))[0])

    def test_el_dia_va_de_17_a_17(self):
        self.assertEqual(dia_de_trading(ny("2025-03-02 18:00")), date(2025, 3, 3))  # domingo por la tarde
        self.assertEqual(dia_de_trading(ny("2025-03-03 16:45")), date(2025, 3, 3))
        self.assertEqual(dia_de_trading(ny("2025-03-03 17:00")), date(2025, 3, 4))

    def test_la_semana_cierra_el_viernes_a_las_17(self):
        clave, fin = clave_y_fin("W1", ny("2025-03-02 18:00"))
        self.assertEqual(clave_y_fin("W1", ny("2025-03-07 16:45"))[0], clave)
        self.assertEqual(fin, ny("2025-03-07 17:00"))

    def test_el_mes_cambia_el_ultimo_dia_a_las_17(self):
        self.assertEqual(clave_y_fin("MN", ny("2025-01-31 16:45"))[0].month, 1)
        self.assertEqual(clave_y_fin("MN", ny("2025-01-31 17:00"))[0].month, 2)

    def test_cambio_de_hora_de_primavera(self):
        # El 9-3-2025 no existen las 2:00; la vela de 4H de la 1 sigue siendo una sola.
        self.assertEqual(clave_y_fin("H4", ny("2025-03-09 01:00"))[0], clave_y_fin("H4", ny("2025-03-09 03:00"))[0])


class LecturaDeCsv(unittest.TestCase):
    def _archivo(self, texto: str) -> str:
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(texto)
        f.close()
        self.addCleanup(os.remove, f.name)
        return f.name

    def test_mt5_en_hora_del_servidor_y_barras_de_1_minuto(self):
        ruta = self._archivo(
            "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
            "2025.01.06\t16:30:00\t100\t101\t99\t100.5\t10\t0\t5\n"
            "2025.01.06\t16:31:00\t100.5\t102\t100\t101\t10\t0\t5\n"
            "2025.01.06\t16:45:00\t101\t101.5\t100.8\t101.2\t10\t0\t5\n"
        )
        barras = leer_csv(ruta)
        self.assertEqual(len(barras), 2)
        b = barras[0]
        self.assertEqual(b.inicio, ny("2025-01-06 09:30"))  # 16:30 del servidor = 9:30 de Nueva York
        self.assertEqual((b.apertura, b.maximo, b.minimo, b.cierre), (100, 102, 99, 101))
        self.assertEqual(barras[1].inicio, ny("2025-01-06 09:45"))
        self.assertEqual((barras[0].i_inicio, barras[1].i_inicio), (0, 1))

    def test_utc_con_horario_de_invierno_y_de_verano(self):
        ruta = self._archivo(
            "timestamp,open,high,low,close\n"
            "2025-07-07T13:30:00Z,1,2,0.5,1.5\n"
            "2025-01-06 14:30:00,1,2,0.5,1.5\n"
        )
        barras = leer_csv(ruta)
        self.assertEqual([b.inicio for b in barras], [ny("2025-01-06 09:30"), ny("2025-07-07 09:30")])

    def test_avisa_si_las_barras_son_de_mas_de_15_minutos(self):
        ruta = self._archivo(
            "timestamp,open,high,low,close\n"
            "2025-01-06 14:00:00,1,2,0.5,1.5\n"
            "2025-01-06 15:00:00,1,2,0.5,1.5\n"
            "2025-01-06 16:00:00,1,2,0.5,1.5\n"
        )
        with self.assertRaises(ValueError):
            leer_csv(ruta)


if __name__ == "__main__":
    unittest.main()
