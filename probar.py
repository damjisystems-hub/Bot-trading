#!/usr/bin/env python3
"""Prueba la estrategia CRT con datos del pasado.

Uso:
  python3 probar.py datos/NAS100_M1.csv --mercado nasdaq
  python3 probar.py datos/EURUSD_M15.csv --mercado eurusd --comparar
  python3 probar.py datos/XAUUSD_M1.csv --mercado oro --operaciones resultados/oro.csv

Los datos pueden ser barras de 1 o de 15 minutos exportadas de MT5 o un CSV con la hora en UTC
(ver README.md).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

from crt.informe import linea_comparacion, texto
from crt.mercados import MERCADOS
from crt.motor import Ajustes, probar
from crt.velas import leer_csv

VARIANTES = (
    ("Base: 1 a 2, espera de 45 min", {}),
    ("1 a 1, como el autor", {"ratio": 1.0}),
    ("Sin espera tras la apertura", {"espera_apertura_min": 0}),
    ("Espera de 30 min", {"espera_apertura_min": 30}),
    ("Espera de 60 min", {"espera_apertura_min": 60}),
    ("Solo después de la apertura", {"solo_tras_apertura": True}),
    ("Diario: basta con que no vaya en contra", {"diario": "no_rojo"}),
)


def guardar_operaciones(ruta: str, res) -> None:
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    d = res.mercado.decimales
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entrada_ny", "salida_ny", "direccion", "sesion", "escenario", "via", "entrada", "stop", "tp", "salida", "resultado", "r"])
        for o in res.operaciones:
            w.writerow([
                f"{o.hora_entrada:%Y-%m-%d %H:%M}",
                f"{o.hora_salida:%Y-%m-%d %H:%M}" if o.hora_salida else "",
                "compra" if o.direccion > 0 else "venta",
                o.sesion,
                o.escenario,
                o.via,
                f"{o.entrada:.{d}f}",
                f"{o.stop:.{d}f}",
                f"{o.tp:.{d}f}",
                f"{o.salida:.{d}f}" if o.salida is not None else "",
                o.resultado,
                f"{o.r:.2f}",
            ])


def main() -> int:
    p = argparse.ArgumentParser(description="Prueba la estrategia CRT con datos del pasado.")
    p.add_argument("datos", help="CSV con las barras de 1 o 15 minutos")
    p.add_argument("--mercado", required=True, choices=sorted(MERCADOS))
    p.add_argument("--formato", default="auto", choices=("auto", "mt5", "utc"))
    p.add_argument("--desfase-servidor", type=int, default=7, help="horas que el servidor de MT5 va por delante de Nueva York (normalmente 7)")
    p.add_argument("--ratio", type=float, default=2.0)
    p.add_argument("--espera", type=int, default=45, help="minutos sin entrar tras la apertura de las 9:30")
    p.add_argument("--diario", default="verde", choices=("verde", "no_rojo"))
    p.add_argument("--solo-tras-apertura", action="store_true")
    p.add_argument("--comparar", action="store_true", help="prueba también las variantes y las compara")
    p.add_argument("--operaciones", help="guarda cada operación en este CSV")
    args = p.parse_args()

    barras = leer_csv(args.datos, args.formato, args.desfase_servidor)
    if not barras:
        print("El archivo no tiene datos.", file=sys.stderr)
        return 1
    mercado = MERCADOS[args.mercado]
    ajustes = Ajustes(
        ratio=args.ratio,
        espera_apertura_min=args.espera,
        diario=args.diario,
        solo_tras_apertura=args.solo_tras_apertura,
    )
    res = probar(barras, mercado, ajustes)
    print(texto(res))
    if args.operaciones:
        guardar_operaciones(args.operaciones, res)
        print(f"\nOperaciones guardadas en {args.operaciones}")
    if args.comparar:
        print("\nComparación de variantes:")
        for nombre, cambios in VARIANTES:
            print(linea_comparacion(nombre, probar(barras, mercado, Ajustes(**cambios))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
