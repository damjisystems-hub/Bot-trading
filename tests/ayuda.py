"""Ayudas para las pruebas: barras de M15 inventadas a partir de un camino de precios."""

from __future__ import annotations

from datetime import datetime, timedelta

from crt.mercados import Mercado
from crt.velas import Vela

# Mercado sin costes, para que las cuentas de las pruebas salgan redondas.
SIN_COSTES = Mercado("PRUEBA", diferencial=0.0, colchon=0.0, decimales=2)


def ny(texto: str) -> datetime:
    return datetime.fromisoformat(texto)


def camino(puntos: list[tuple[str, float]]) -> list[Vela]:
    """Barras de M15 que siguen un camino de precios en línea recta entre puntos (hora de Nueva
    York, precio). Las horas de los puntos tienen que ser múltiplos de 15 minutos."""
    barras: list[Vela] = []
    for (t0, p0), (t1, p1) in zip(puntos, puntos[1:]):
        t0, t1 = ny(t0), ny(t1)
        pasos = int((t1 - t0) / timedelta(minutes=15))
        for k in range(pasos):
            a = p0 + (p1 - p0) * k / pasos
            b = p0 + (p1 - p0) * (k + 1) / pasos
            i = len(barras)
            barras.append(Vela(t0 + timedelta(minutes=15 * k), a, max(a, b), min(a, b), b, i, i))
    return barras


def espejo(puntos: list[tuple[str, float]], eje: float = 200.0) -> list[tuple[str, float]]:
    """El mismo camino al revés (lo que sube baja), para probar las ventas."""
    return [(t, eje - p) for t, p in puntos]
