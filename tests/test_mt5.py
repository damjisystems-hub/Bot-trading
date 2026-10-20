"""El bot de MT5 y el Python tienen que escribir la misma memoria: mismas columnas, mismos motivos,
mismos resultados y mismas banderas rojas."""

import os
import re
import unittest

from crt import memoria, motor

RUTA_EA = os.path.join(os.path.dirname(__file__), "..", "mt5", "BotCRT.mq5")


def _fuente() -> str:
    with open(RUTA_EA, encoding="utf-8-sig") as f:
        return f.read()


def _textos_de(funcion: str) -> set:
    cuerpo = re.search(rf"string {funcion}\(const int \w+\)(.*?)\n  }}", _fuente(), re.S)[1]
    return set(re.findall(r'return "([^"]+)";', cuerpo))


class MismaMemoria(unittest.TestCase):
    def test_mismas_columnas(self):
        cabecera = re.search(r'#define CABECERA_MEMORIA\s+"([^"]+)"', _fuente())[1]
        self.assertEqual(cabecera.split(","), memoria.COLUMNAS)

    def test_mismos_motivos(self):
        self.assertEqual(_textos_de("TextoDecision"), set(motor.DECISIONES))

    def test_mismos_resultados(self):
        self.assertEqual(_textos_de("TextoResultado"), set(motor.RESULTADOS))

    def test_mismas_banderas(self):
        self.assertEqual(_textos_de("TextoBandera"), set(motor.BANDERAS))

    def test_el_archivo_lleva_bom_para_que_metaeditor_lea_los_acentos(self):
        with open(RUTA_EA, "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")


if __name__ == "__main__":
    unittest.main()
