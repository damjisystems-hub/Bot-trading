import os
import tempfile
import unittest

from crt import cuaderno

CABECERA = "fecha,mercado,direccion,cuenta,siguio_el_plan,regla_rota,emocion,resultado,r,nota\n"


class Cuaderno(unittest.TestCase):
    def _leer(self, filas: str):
        ruta = os.path.join(tempfile.mkdtemp(), "operaciones.csv")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(CABECERA + filas)
        return cuaderno.leer(ruta)

    def test_lee_y_cuenta(self):
        apuntes = self._leer(
            "2026-10-02 10:30,nasdaq,venta,demo,si,,calma,SL,-1,\n"
            "2026-10-01 09:00,nasdaq,compra,demo,si,,calma,TP,2,\n"
            '2026-10-02 11:00,nasdaq,venta,demo,no,sin rango de 1H,venganza,TP,"1,5",\n'
            "2026-10-03 10:30,oro,compra,propia,sí,,dudas,BE,0,\n"
        )
        self.assertEqual([a.r for a in apuntes], [2.0, -1.0, 1.5, 0.0])  # ordenadas por fecha
        texto = cuaderno.informe(apuntes)
        self.assertIn("4 operaciones", texto)
        self.assertIn("Ganadas saltándose el plan: 1", texto)
        self.assertIn("Perdidas siguiendo el plan: 1", texto)
        self.assertIn("Días bien hechos (todo siguiendo el plan): 2 de 3", texto)
        self.assertIn("Después de una pérdida, la siguiente operación siguió el plan el 0 %", texto)
        self.assertIn("sin rango de 1H", texto)
        self.assertIn("- demo: desde el 01-10-2026", texto)

    def test_avisa_de_lo_que_no_vale(self):
        with self.assertRaises(ValueError):
            self._leer("2026-10-01,nasdaq,compra,demo,quizá,,calma,TP,2,\n")
        with self.assertRaises(ValueError):
            self._leer("2026-10-01,nasdaq,compra,real,si,,calma,TP,2,\n")
        with self.assertRaises(ValueError):
            self._leer("2026-10-01,nasdaq,compra,demo,si,,calma,TP,dos,\n")

    def test_vacio(self):
        self.assertIn("vacío", cuaderno.informe(self._leer("")))

    def test_la_plantilla_del_repositorio_se_lee(self):
        ruta = os.path.join(os.path.dirname(__file__), "..", "cuaderno", "operaciones.csv")
        self.assertEqual(cuaderno.leer(ruta), [])


if __name__ == "__main__":
    unittest.main()
