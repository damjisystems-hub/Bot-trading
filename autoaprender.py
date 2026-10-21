#!/usr/bin/env python3
"""Autoaprender: el bot repasa todo lo vivido, busca sus peores situaciones y aprende a no entrar en ellas, con
frenos para no aprender la suerte (ver crt/autoaprendizaje.py).

Uso:
  python3 autoaprender.py --carpeta "<carpeta de datos de MT5>/MQL5/Files/BotCRT"
      Lee los precios que exporta el bot de MT5 cada día (barras_ny_<mercado>.csv) y escribe allí
      reglas_aprendidas.txt, que el bot lee solo cada día. El informe queda en informe_autoaprendizaje.txt.
  python3 autoaprender.py datos/EURUSD_M1.csv --mercado eurusd
      Con otros precios (de MT5, de Dukascopy o en UTC). Escribe resultados/reglas_aprendidas.txt.

Para el Mac hay un atajo: doble clic en Autoaprender.command.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

from crt import autoaprendizaje
from crt.mercados import MERCADOS
from crt.velas import leer_csv


def nombre_de_archivo(nombre: str) -> str:
    """Lo mismo que NombreDeArchivo del bot de MT5: «EUR/USD» → «EUR_USD»."""
    return re.sub(r'[\\/:*?"<>| ]', "_", nombre)


def mercado_del_archivo(ruta: str) -> str | None:
    """«barras_ny_Oro_(XAU_USD).csv» → «oro». Si el nombre no es el de un mercado del bot, None."""
    base = os.path.basename(ruta)[len("barras_ny_") : -len(".csv")]
    for clave, m in MERCADOS.items():
        if base in (nombre_de_archivo(m.nombre), clave, clave.upper()):
            return clave
    return None


def aprender_uno(barras, clave: str, ruta_reglas: str) -> str:
    informe = autoaprendizaje.aprender(barras, MERCADOS[clave])
    nuevas, desaprendidas = autoaprendizaje.escribir_reglas(ruta_reglas, informe)
    lineas = [autoaprendizaje.texto(informe)]
    if nuevas:
        lineas.append("NUEVO: " + "; ".join(f"{a} = {v}" for a, v in nuevas))
    if desaprendidas:
        lineas.append("DESAPRENDIDO (ya no se cumple): " + "; ".join(f"{a} = {v}" for a, v in desaprendidas))
    return "\n".join(lineas)


def main() -> int:
    p = argparse.ArgumentParser(description="El bot aprende solo de sus peores situaciones, con frenos.")
    p.add_argument("datos", nargs="?", help="CSV con barras de 1 o 15 minutos")
    p.add_argument("--mercado", choices=sorted(MERCADOS))
    p.add_argument("--carpeta", help="la carpeta MQL5/Files/BotCRT del bot de MT5")
    p.add_argument("--formato", default="auto", choices=("auto", "mt5", "utc"))
    p.add_argument("--desfase-servidor", type=int, default=7)
    args = p.parse_args()

    if args.carpeta:
        archivos = sorted(glob.glob(os.path.join(args.carpeta, "barras_ny_*.csv")))
        if not archivos:
            p.error(f"no hay barras_ny_*.csv en {args.carpeta}: el bot de MT5 los escribe con ExportarBarras")
        ruta_reglas = os.path.join(args.carpeta, autoaprendizaje.ARCHIVO)
        textos = []
        for ruta in archivos:
            clave = mercado_del_archivo(ruta)
            if clave is None:
                textos.append(f"{os.path.basename(ruta)}: no sé qué mercado es (poned NombreMercado como en mt5/LEEME.md).")
                continue
            # El bot de MT5 los escribe ya en hora de Nueva York: desfase 0.
            textos.append(aprender_uno(leer_csv(ruta, "mt5", 0), clave, ruta_reglas))
        texto = "\n\n".join(textos)
        with open(os.path.join(args.carpeta, "informe_autoaprendizaje.txt"), "w", encoding="utf-8") as f:
            f.write(texto + "\n")
        print(texto)
        print(f"\nReglas en {ruta_reglas}. El bot de MT5 las lee solo cada día.")
        return 0

    if not args.datos or not args.mercado:
        p.error("hacen falta los datos y --mercado (o --carpeta)")
    ruta_reglas = os.path.join("resultados", autoaprendizaje.ARCHIVO)
    print(aprender_uno(leer_csv(args.datos, args.formato, args.desfase_servidor), args.mercado, ruta_reglas))
    print(f"\nReglas en {ruta_reglas}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
