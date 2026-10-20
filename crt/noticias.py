"""Noticias fuertes (FOMC, NFP, IPC…) para avisar y para probar la regla «no operar esos días».

El archivo lo puede exportar el bot de MT5 desde su calendario económico (parámetro ExportarNoticias)
con las columnas fecha, hora, moneda, evento e importancia, con la fecha y la hora de Nueva York.
"""

from __future__ import annotations

import csv
from datetime import date


def leer_noticias(ruta: str, monedas: tuple = ("USD",)) -> dict[date, list[str]]:
    """{fecha de Nueva York: [nombres de las noticias de importancia alta de esas monedas]}."""
    noticias: dict[date, list[str]] = {}
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for fila in csv.DictReader(f):
            if fila.get("importancia", "").strip().lower() != "alta":
                continue
            if fila.get("moneda", "").strip().upper() not in monedas:
                continue
            fecha = date.fromisoformat(fila["fecha"].strip())
            nombre = f"{fila.get('hora', '').strip()} {fila.get('evento', '').strip()}".strip()
            noticias.setdefault(fecha, []).append(nombre)
    return noticias
