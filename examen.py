#!/usr/bin/env python3
"""Examen: el bot se pone a prueba con las situaciones de casos/casos.csv y explica lo que hizo.

Uso:
  python3 examen.py datos/NAS100_M1.csv --mercado nasdaq
  python3 examen.py datos/EURUSD_M1.csv --mercado eurusd --casos casos/casos.csv

Los datos tienen que empezar unos meses antes de los casos, para que el bot tenga el semanal y el
mensual formados.

Con --modelo-del-backtest se examina con el modelo del vídeo del backtest del autor (sin sesgo ni diario
y hasta 3 operaciones al día): sirve para los casos «vbacktest-…», que salen de ese modelo.
"""

from __future__ import annotations

import argparse
import sys

from crt import casos
from crt.mercados import MERCADOS
from crt.motor import Ajustes, probar
from crt.noticias import leer_noticias
from crt.velas import leer_csv


def main() -> int:
    p = argparse.ArgumentParser(description="Examina al bot con situaciones reales.")
    p.add_argument("datos", help="CSV con barras de 1 o 15 minutos")
    p.add_argument("--mercado", required=True, choices=sorted(MERCADOS))
    p.add_argument("--casos", default="casos/casos.csv")
    p.add_argument("--formato", default="auto", choices=("auto", "mt5", "utc"))
    p.add_argument("--desfase-servidor", type=int, default=7)
    p.add_argument("--noticias", help="CSV de noticias, para que la memoria las tenga en cuenta")
    p.add_argument("--modelo-del-backtest", action="store_true", help="sin sesgo ni diario y hasta 3 operaciones al día")
    args = p.parse_args()

    mercado = MERCADOS[args.mercado]
    lista = [c for c in casos.leer_casos(args.casos) if c.mercado == args.mercado]
    noticias = leer_noticias(args.noticias, mercado.monedas) if args.noticias else None
    ajustes = Ajustes(ignorar_sesgo=True, diario="ignorar", max_operaciones_dia=3) if args.modelo_del_backtest else None
    res = probar(leer_csv(args.datos, args.formato, args.desfase_servidor), mercado, ajustes, noticias)
    print(casos.texto(lista, res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
