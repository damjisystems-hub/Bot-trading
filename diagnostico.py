#!/usr/bin/env python3
"""Diagnóstico: ¿tiene ventaja un rango CRT por sí solo, sin los filtros del bot? (ver crt/diagnostico.py)

Uso:
  python3 diagnostico.py datos/EURUSD_M1.csv --mercado eurusd
  python3 diagnostico.py datos/NAS100_M1.csv --mercado nasdaq --marco D1
"""

from __future__ import annotations

import argparse
import sys

from crt import diagnostico
from crt.mercados import MERCADOS
from crt.velas import leer_csv


def main() -> int:
    p = argparse.ArgumentParser(description="Mira si un rango CRT, por sí solo, tiene ventaja.")
    p.add_argument("datos", help="CSV con barras de 1 o 15 minutos")
    p.add_argument("--mercado", required=True, choices=sorted(MERCADOS))
    p.add_argument("--marco", default="H4", choices=("H1", "H3", "H4", "D1"))
    p.add_argument("--formato", default="auto", choices=("auto", "mt5", "utc"))
    p.add_argument("--desfase-servidor", type=int, default=7)
    args = p.parse_args()
    mercado = MERCADOS[args.mercado]
    barras = leer_csv(args.datos, args.formato, args.desfase_servidor)
    print(diagnostico.texto(mercado.nombre, args.marco, diagnostico.rangos_en_bruto(barras, mercado, args.marco)))
    print("Las cifras dependen de los datos y de los costes supuestos de cada mercado (crt/mercados.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
