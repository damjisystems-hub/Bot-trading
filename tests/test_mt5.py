"""El bot de MT5 y el Python tienen que escribir la misma memoria: mismas columnas y mismos motivos."""

import os
import re
import unittest

from crt import memoria, motor

RUTA_EA = os.path.join(os.path.dirname(__file__), "..", "mt5", "BotCRT.mq5")


def _fuente() -> str:
    with open(RUTA_EA, encoding="utf-8-sig") as f:
        return f.read()


class MismaMemoria(unittest.TestCase):
    def test_mismas_columnas(self):
        cabecera = re.search(r'#define CABECERA_MEMORIA\s+"([^"]+)"', _fuente())[1]
        self.assertEqual(cabecera.split(","), memoria.COLUMNAS)

    def test_mismos_motivos(self):
        cuerpo = re.search(r"string TextoDecision\(const int d\)(.*?)\n  }", _fuente(), re.S)[1]
        en_mt5 = set(re.findall(r'return "([^"]+)";', cuerpo))
        en_python = {v for k, v in vars(motor).items() if k.isupper() and isinstance(v, str) and k != "__doc__"}
        self.assertEqual(en_mt5, en_python)

    def test_el_archivo_lleva_bom_para_que_metaeditor_lea_los_acentos(self):
        with open(RUTA_EA, "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")


if __name__ == "__main__":
    unittest.main()
