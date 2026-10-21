"""La memoria del bot en un archivo CSV que se abre con Excel o Numbers.

Una fila por situación vista: la primera vez que una idea de 4H da un order block en horario (se tome
o no, y por qué) y cada entrada. Las descartadas llevan el resultado que habrían tenido. Cada fila lleva
cómo estaban el 3H y el 1H, las banderas rojas y la nota de la situación (A, B o C). El bot de MT5
escribe el mismo archivo con las mismas columnas, así que el informe de aprendizaje sirve para los dos.
"""

from __future__ import annotations

import csv
import os

from .motor import DIAS, SESGO, Resultado

COLUMNAS = [
    "mercado", "hora_ny", "direccion", "decision", "sesion", "dia_semana",
    "sesgo_semanal", "sesgo_mensual", "diario", "via_diario", "via_4h", "h3", "h1", "escenario",
    "vela1_rel", "stop_rel", "objetivo_r", "noticias", "banderas", "nota",
    "entrada", "stop", "tp", "resultado", "r", "mfe_r", "mae_r", "tomada",
]  # fmt: skip


def _numero(x: float | None) -> str:
    return "" if x is None else f"{x:.2f}"


def filas(res: Resultado) -> list[dict]:
    dec = res.mercado.decimales
    salida = []
    for s in res.senales:
        op = s.operacion
        cerrada = op is not None and bool(op.resultado)
        salida.append({
            "mercado": res.mercado.nombre,
            "hora_ny": f"{s.hora:%Y-%m-%d %H:%M}",
            "direccion": "compra" if s.direccion > 0 else "venta",
            "decision": s.decision,
            "sesion": s.sesion,
            "dia_semana": DIAS[s.hora.weekday()],
            "sesgo_semanal": SESGO[s.sesgo_semanal],
            "sesgo_mensual": SESGO[s.sesgo_mensual],
            "diario": s.diario,
            "via_diario": s.via_diario,
            "via_4h": s.via_4h,
            "h3": s.h3,
            "h1": s.h1,
            "escenario": s.escenario,
            "vela1_rel": _numero(s.vela1_rel),
            "stop_rel": _numero(s.stop_rel),
            "objetivo_r": _numero(s.objetivo_r),
            "noticias": s.noticias,
            "banderas": " | ".join(s.banderas),
            "nota": s.nota,
            "entrada": f"{op.entrada:.{dec}f}" if op else "",
            "stop": f"{op.stop_inicial:.{dec}f}" if op else "",
            "tp": f"{op.tp:.{dec}f}" if op else "",
            "resultado": op.resultado if op else "",
            "r": _numero(op.r) if cerrada else "",
            "mfe_r": _numero(op.mfe_r) if cerrada else "",
            "mae_r": _numero(op.mae_r) if cerrada else "",
            "tomada": "si" if op is not None and op.tomada else "no",
        })  # fmt: skip
    return salida


def guardar(ruta: str, filas_: list[dict]) -> None:
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas_)


def leer(ruta: str) -> list[dict]:
    """Lee una memoria (la del Python o la del bot de MT5)."""
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        return [dict(fila) for fila in csv.DictReader(f)]
