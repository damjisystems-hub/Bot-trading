"""Diagnóstico: ¿tiene ventaja un rango CRT por sí solo, sin los filtros del bot?

Para cada rango que forma un marco (por ejemplo, el de 4H), se entra al cierre de la vela 2 con el stop en
el barrido y el TP en el objetivo (el extremo de la vela 1), y se mira qué toca antes. Sin sesgo, ni diario,
ni order block: la idea en bruto. Si el precio se moviera al azar, llegaría al objetivo tantas veces como
riesgo / (riesgo + recompensa) y la media sería 0 R menos los costes. Si los rangos tienen ventaja, tiene
que salir por encima de eso.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from .marcos import Marco
from .mercados import Mercado
from .velas import Vela


@dataclass
class RangoEnBruto:
    hora: datetime  # cierre de la barra con la que se formó
    direccion: int
    objetivo_r: float  # a cuántas veces el riesgo está el objetivo
    r: float = 0.0  # resultado: el objetivo en R o −1


def rangos_en_bruto(barras: list[Vela], mercado: Mercado, marco: str = "H4") -> list[RangoEnBruto]:
    m = Marco(marco)
    dif = mercado.diferencial
    abiertos: list[tuple] = []  # (RangoEnBruto, entrada, stop, objetivo)
    hechos: list[RangoEnBruto] = []

    def nuevo(evento, barra: Vela) -> None:
        if evento is None or evento.tipo != "rango":
            return
        d = evento.direccion
        entrada = barra.cierre + (dif if d > 0 else 0.0)  # se compra al precio de compra
        stop = evento.barrido - d * mercado.colchon + (0.0 if d > 0 else dif)
        objetivo = evento.objetivo if d > 0 else evento.objetivo + dif  # las ventas se cierran comprando
        riesgo, recompensa = (entrada - stop) * d, (objetivo - entrada) * d
        if riesgo > 0 and recompensa > 0:
            abiertos.append((RangoEnBruto(barra.inicio, d, recompensa / riesgo), entrada, stop, objetivo))

    for b in barras:
        if m.toca_cerrar_antes(b):
            nuevo(m.cerrar(), b)
        for abierto in list(abiertos):
            rango, _, stop, objetivo = abierto
            d = rango.direccion
            alto, bajo = (b.maximo, b.minimo) if d > 0 else (b.maximo + dif, b.minimo + dif)
            if (bajo <= stop) if d > 0 else (alto >= stop):  # si toca los dos en la misma barra, cuenta el stop
                rango.r = -1.0
            elif (alto >= objetivo) if d > 0 else (bajo <= objetivo):
                rango.r = rango.objetivo_r
            else:
                continue
            hechos.append(rango)
            abiertos.remove(abierto)
        m.actualizar_con_barra(b)
        m.sumar(b)
        if m.toca_cerrar_despues(b):
            nuevo(m.cerrar(), b)
    return hechos


def _linea(nombre: str, grupo: list[RangoEnBruto]) -> str:
    n = len(grupo)
    if not n:
        return f"  {nombre:<25}     0"
    llegan = sum(1 for g in grupo if g.r > 0) / n
    azar = sum(1 / (1 + g.objetivo_r) for g in grupo) / n  # lo que llegaría si el precio fuera al azar
    media = sum(g.r for g in grupo) / n
    return (
        f"  {nombre:<25}{n:>6} · llega al objetivo el {100 * llegan:4.1f} % (al azar, el {100 * azar:4.1f} %) · "
        f"media {media:+.3f} R".replace(".", ",")
    )


def texto(nombre_mercado: str, marco: str, hechos: list[RangoEnBruto]) -> str:
    lineas = [
        f"Rangos de {marco} en bruto · {nombre_mercado}: entrada al cierre de la vela 2, stop en el barrido y TP en el objetivo.",
        _linea("todos", hechos),
    ]
    grupos: dict = defaultdict(list)
    for h in hechos:
        grupos["objetivo a menos de 1 R" if h.objetivo_r < 1 else ("objetivo de 1 a 2 R" if h.objetivo_r < 2 else "objetivo a 2 R o más")].append(h)
    lineas += [_linea(k, grupos[k]) for k in sorted(grupos)]
    lineas += [_linea("compras", [h for h in hechos if h.direccion > 0]), _linea("ventas", [h for h in hechos if h.direccion < 0])]
    lineas.append(
        "Si «llega al objetivo» sale parecido a «al azar» y la media queda en 0 o por debajo, el rango solo no da ventaja: "
        "la ventaja tendría que venir de los filtros (sesgo, diario, order block…)."
    )
    return "\n".join(lineas)
