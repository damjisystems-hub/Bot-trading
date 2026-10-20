#!/usr/bin/env python3
"""Aprender: prueba con el pasado + lo que enseña la memoria + laboratorio de reglas candidatas.

Uso:
  python3 aprender.py datos/NAS100_M1.csv --mercado nasdaq
  python3 aprender.py datos/NAS100_M1.csv --mercado nasdaq --noticias datos/noticias.csv --corte 2025-06-01
  python3 aprender.py --memoria-mt5 datos/memoria_NAS100.csv      (solo lo que apuntó el bot de MT5)

Guarda la memoria en resultados/memoria_<mercado>.csv. Nada de esto cambia las reglas: propone.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from crt import aprendizaje, laboratorio, memoria
from crt.informe import texto as texto_prueba
from crt.mercados import MERCADOS
from crt.noticias import leer_noticias
from crt.velas import leer_csv


def main() -> int:
    p = argparse.ArgumentParser(description="Aprende de la memoria y prueba reglas candidatas.")
    p.add_argument("datos", nargs="?", help="CSV con barras de 1 o 15 minutos")
    p.add_argument("--mercado", choices=sorted(MERCADOS))
    p.add_argument("--formato", default="auto", choices=("auto", "mt5", "utc"))
    p.add_argument("--desfase-servidor", type=int, default=7)
    p.add_argument("--noticias", help="CSV de noticias (fecha, hora, moneda, evento, importancia)")
    p.add_argument("--corte", help="fecha que separa los dos periodos del laboratorio (AAAA-MM-DD)")
    p.add_argument("--memoria-mt5", help="memoria escrita por el bot de MT5: solo se hace el informe")
    args = p.parse_args()

    if args.memoria_mt5:
        print(aprendizaje.informe(memoria.leer(args.memoria_mt5)))
        return 0
    if not args.datos or not args.mercado:
        p.error("hacen falta los datos y --mercado (o --memoria-mt5)")

    mercado = MERCADOS[args.mercado]
    barras = leer_csv(args.datos, args.formato, args.desfase_servidor)
    noticias = leer_noticias(args.noticias, mercado.monedas) if args.noticias else None
    corte = datetime.fromisoformat(args.corte) if args.corte else None

    corte, base, pruebas = laboratorio.comprobar(barras, mercado, noticias=noticias, corte=corte)
    filas = memoria.filas(base.resultado)
    ruta = f"resultados/memoria_{args.mercado}.csv"
    memoria.guardar(ruta, filas)

    print(texto_prueba(base.resultado))
    print("\n" + aprendizaje.informe(filas))
    print("\n" + laboratorio.texto(corte, base, pruebas, hay_noticias=bool(noticias)))
    print(f"\nMemoria guardada en {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
