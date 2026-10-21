#!/usr/bin/env python3
"""Prueba con el pasado de varios mercados a la vez, como el bot de MT5 puesto en todos los gráficos.

El tope de pérdida del día suma lo de todos los mercados (en probar.py cada mercado va solo). Saca el
resultado de cada mercado, el de todos juntos, la peor caída de la cuenta y los días que se llegó al
tope. También cuenta las veces que el euro y la libra estaban abiertos a la vez y hacia el mismo lado:
se mueven casi igual, así que eso es arriesgar casi el doble en la misma idea.

Uso:
  python3 cartera.py datos/eurusd_M15_utc.csv:eurusd datos/gbpusd_M15_utc.csv:gbpusd \\
                     datos/nasdaq_M15_utc.csv:nasdaq datos/oro_M15_utc.csv:oro --formato utc
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from crt.informe import estadisticas
from crt.mercados import MERCADOS
from crt.motor import Ajustes, probar_cartera
from crt.velas import QUINCE_MIN, dia_de_trading, leer_csv


def _r(x: float) -> str:
    return f"{x:+.1f} R".replace(".", ",")


def _pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def _linea(nombre: str, ops: list) -> str:
    e = estadisticas(ops)
    return (
        f"  {nombre:<16}{e['n']:>5} op. · acierto {_pct(e['acierto']):>5} · {_r(e['total']):>9} · "
        f"media {_r(e['media']):>7} · peor caída {_r(-e['caida']):>8} · peor racha {e['racha']}"
    )


def a_la_vez(a: list, b: list) -> list[tuple]:
    """Parejas de operaciones de dos mercados abiertas a la vez y hacia el mismo lado."""
    return [
        (x, y)
        for x in a
        for y in b
        if x.direccion == y.direccion and x.hora_entrada < y.hora_salida and y.hora_entrada < x.hora_salida
    ]


def informe(resultados: dict, ajustes: Ajustes) -> str:
    todas = sorted((o for r in resultados.values() for o in r.operaciones), key=lambda o: o.hora_salida)
    lineas = ["Prueba con el pasado de todos los mercados a la vez (tope de pérdida del día entre todos)", ""]
    for nombre, res in resultados.items():
        lineas.append(_linea(res.mercado.nombre, res.operaciones))
    lineas += [_linea("Todos juntos", todas), ""]
    por_dia: defaultdict = defaultdict(float)
    for o in todas:
        por_dia[dia_de_trading(o.hora_salida - QUINCE_MIN)] += o.r
    if por_dia:
        peor = min(por_dia, key=por_dia.get)
        lineas.append(f"Peor día: {peor:%d-%m-%Y} con {_r(por_dia[peor])}.")
    if ajustes.perdida_max_dia_r:
        topes = sum(1 for r in por_dia.values() if r <= -ajustes.perdida_max_dia_r)
        lineas.append(f"Días que se llegó al tope de {ajustes.perdida_max_dia_r:g} R entre todos: {topes} de {len(por_dia)} días con operaciones.")
    if "eurusd" in resultados and "gbpusd" in resultados:
        parejas = a_la_vez(resultados["eurusd"].operaciones, resultados["gbpusd"].operaciones)
        if parejas:
            juntas = sum(x.r + y.r for x, y in parejas)
            iguales = sum(1 for x, y in parejas if (x.r > 0) == (y.r > 0))
            lineas.append(
                f"Euro y libra abiertos a la vez y hacia el mismo lado: {len(parejas)} veces, con {_r(juntas)} entre los dos; "
                f"en {iguales} de ellas acabaron igual (las dos ganan o las dos pierden)."
            )
        else:
            lineas.append("Euro y libra no han coincidido nunca abiertos a la vez hacia el mismo lado.")
    lineas += [
        "",
        "Las cifras dependen de los datos y de los costes supuestos de cada mercado (crt/mercados.py).",
        "1 R es lo que se arriesga en cada operación (el 1 % de la cuenta).",
    ]
    return "\n".join(lineas)


def main() -> int:
    p = argparse.ArgumentParser(description="Prueba varios mercados a la vez con el tope de pérdida compartido.")
    p.add_argument("datos", nargs="+", help="archivo:mercado, por ejemplo datos/EURUSD_M1.csv:eurusd")
    p.add_argument("--formato", default="auto", choices=("auto", "mt5", "utc"))
    p.add_argument("--desfase-servidor", type=int, default=7)
    args = p.parse_args()
    mercados = {}
    for dato in args.datos:
        ruta, _, nombre = dato.rpartition(":")
        if nombre not in MERCADOS or not ruta:
            p.error(f"«{dato}»: tiene que ser archivo:mercado, con mercado uno de {', '.join(sorted(MERCADOS))}")
        mercados[nombre] = (leer_csv(ruta, args.formato, args.desfase_servidor), MERCADOS[nombre])
    ajustes = Ajustes()
    print(informe(probar_cartera(mercados, ajustes), ajustes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
