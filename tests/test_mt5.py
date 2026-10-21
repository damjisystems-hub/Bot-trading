"""El bot de MT5 y el Python tienen que escribir la misma memoria (mismas columnas, mismos motivos,
mismos resultados y mismas banderas rojas, en el mismo orden) y tener los mismos ajustes."""

import os
import re
import unittest
from dataclasses import fields

from crt import memoria, motor

RUTA_EA = os.path.join(os.path.dirname(__file__), "..", "mt5", "BotCRT.mq5")


def _fuente() -> str:
    with open(RUTA_EA, encoding="utf-8-sig") as f:
        return f.read()


def _textos_de(funcion: str) -> set:
    cuerpo = re.search(rf"string {funcion}\(const int \w+\)(.*?)\n  }}", _fuente(), re.S)[1]
    return set(re.findall(r'return "([^"]+)";', cuerpo))


# Cada ajuste del Python con su parámetro en el bot de MT5 (sesgo_fijo es solo para las pruebas).
PARAMETROS = {
    "ratio": "Ratio",
    "espera_apertura_min": "EsperaAperturaMin",
    "desde": "HoraDesde",
    "hasta": "HoraHasta",
    "solo_tras_apertura": "SoloTrasApertura",
    "solo_londres": "SoloLondres",
    "diario": ("DiarioBastaNoRojo", "DiarioValeExpansiva", "IgnorarDiario"),
    "comprobar_objetivo_diario": "ComprobarObjetivoDiario",
    "max_operaciones_dia": "MaxOperacionesDia",
    "perdida_max_dia_r": "PerdidaMaxDiaR",
    "inicio_4h": "HoraInicio4H",
    "stop_a_entrada_en_r": "StopAEntradaEnR",
    "vela1_minima": "Vela1Minima",
    "escenarios": "EscenariosPermitidos",
    "sin_noticias": "SinNoticias",
    "salida_1h": "Salida1H",
    "salida_peligro": "SalidaPeligro",
    "tp_hasta_objetivo_4h": "TpHastaObjetivo4H",
    "no_perseguir": "NoPerseguir",
    "apertura_del_dia": "SoloLadoDeLaApertura",
    "antes_de_noticias": "AntesDeNoticias",
    "cierre_diario": "CierreDiario",
    "salida_por_tiempo": "SalidaPorTiempo",
    "be_antes_de_las_9": "BreakEvenAntesDeLas9",
    "comprobar_objetivo_4h": "ComprobarObjetivo4H",
    "ignorar_sesgo": "IgnorarSesgo",
    "vetar_tomando": "VetarTomando",
    "tp_objetivo_4h": "TpEnObjetivo4H",
    "exigir_1h": "Exigir1H",
    "exigir_3h": "Exigir3H",
    "sin_banderas": "SoloSinBanderas",
    "max_banderas": "MaxBanderas",
    "pausa_tras_stops": "PausaTrasStops",
    "tolerancia_diario": "ToleranciaDiario",
    "sesgo_fijo": (),
}


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

    def test_las_banderas_van_en_el_mismo_orden(self):
        # El bot de MT5 las escribe por orden de bit; el Python, en el orden de BANDERAS.
        fuente = _fuente()
        bits = {nombre: int(valor) for nombre, valor in re.findall(r"#define (BAN_\w+)\s+(\d+)", fuente)}
        cuerpo = re.search(r"string TextoBandera\(const int \w+\)(.*?)\n  }", fuente, re.S)[1]
        textos = dict(re.findall(r'case (BAN_\w+):\s*return "([^"]+)";', cuerpo))
        orden = [textos[n] for n in sorted(textos, key=bits.get)]
        self.assertEqual(orden, list(motor.BANDERAS))
        self.assertEqual(sorted(bits[n] for n in textos), [1 << k for k in range(len(motor.BANDERAS))])
        self.assertEqual(int(re.search(r"#define NUM_BANDERAS\s+(\d+)", fuente)[1]), len(motor.BANDERAS))

    def test_cada_ajuste_tiene_su_parametro(self):
        self.assertEqual({f.name for f in fields(motor.Ajustes)}, set(PARAMETROS))
        entradas = set(re.findall(r"^input\s+\w+\s+(\w+)", _fuente(), re.M))
        for ajuste, nombres in PARAMETROS.items():
            for nombre in (nombres,) if isinstance(nombres, str) else nombres:
                self.assertIn(nombre, entradas, f"falta el parámetro de MT5 para «{ajuste}»")

    def test_el_archivo_lleva_bom_para_que_metaeditor_lea_los_acentos(self):
        with open(RUTA_EA, "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")


if __name__ == "__main__":
    unittest.main()
