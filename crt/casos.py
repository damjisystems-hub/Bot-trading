"""Examen: situaciones reales que el equipo le enseña al bot (de los vídeos o de lo que pase), con lo que
tenía que hacer. El bot se examina con todas cada vez y explica lo que hizo y por qué.

Un fallo no cambia las reglas solo: es una pista. Se mira por qué falló y, si hace falta una regla
nueva, se prueba en el laboratorio y la aprueba el equipo.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime

from .motor import Resultado

ESPERADOS = ("compra", "venta", "nada", "no compra", "no venta")
NOMBRE_DIR = {+1: "compras", -1: "ventas"}
NOMBRE_SESGO = {+1: "compras", -1: "ventas", 0: "sin sesgo"}


@dataclass
class Caso:
    id: str
    mercado: str  # nasdaq, eurusd u oro
    desde: datetime | None  # hora de Nueva York
    hasta: datetime | None
    esperado: str
    fuente: str
    nota: str


def _hora(texto: str) -> datetime | None:
    texto = (texto or "").strip()
    return datetime.fromisoformat(texto) if texto else None


def leer_casos(ruta: str) -> list[Caso]:
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        casos = []
        for fila in csv.DictReader(f):
            esperado = fila["esperado"].strip().lower()
            if esperado not in ESPERADOS:
                raise ValueError(f"Caso {fila['id']}: «{esperado}» no vale; tiene que ser uno de {ESPERADOS}")
            casos.append(Caso(
                fila["id"].strip(), fila["mercado"].strip().lower(), _hora(fila["desde"]), _hora(fila["hasta"]),
                esperado, fila.get("fuente", "").strip(), fila.get("nota", "").strip(),
            ))  # fmt: skip
        return casos


def examinar(caso: Caso, res: Resultado) -> tuple[str, list[str]]:
    """Devuelve el estado («bien», «mal», «sin datos» o «falta la fecha») y la explicación."""
    if caso.desde is None or caso.hasta is None:
        return "falta la fecha", []
    if res.desde is None or caso.desde < res.desde or caso.hasta > res.hasta:
        return "sin datos", []
    entradas = [o for o in res.operaciones if caso.desde <= o.hora_entrada <= caso.hasta]
    compras = [o for o in entradas if o.direccion > 0]
    ventas = [o for o in entradas if o.direccion < 0]
    bien = {
        "compra": bool(compras),
        "venta": bool(ventas),
        "nada": not entradas,
        "no compra": not compras,
        "no venta": not ventas,
    }[caso.esperado]

    explicacion = []
    for o in entradas:
        explicacion.append(
            f"{'Compró' if o.direccion > 0 else 'Vendió'} a las {o.hora_entrada:%H:%M} del {o.hora_entrada:%d-%m} "
            f"({o.sesion.lower()}, escenario {o.escenario}): {o.resultado or 'abierta'} {o.r:+.1f} R".replace(".", ",")
        )
    for s in res.senales:
        if caso.desde <= s.hora <= caso.hasta and s.decision != "entrada":
            explicacion.append(f"A las {s.hora:%H:%M} del {s.hora:%d-%m} no {'compró' if s.direccion > 0 else 'vendió'}: {s.decision}.")
    foto = next((f for f in res.fotos if f.hora >= caso.desde), None)
    if foto is not None and foto.hora <= caso.hasta:
        explicacion.append(
            f"A las {foto.hora:%H:%M} el sesgo era de {NOMBRE_SESGO[foto.sesgo]}; diario: compras {foto.diario[1]}, "
            f"ventas {foto.diario[-1]}; 4H: compras {foto.h4[1]}, ventas {foto.h4[-1]}."
        )
    if not entradas and not any(caso.desde <= s.hora <= caso.hasta for s in res.senales):
        explicacion.append("No hubo ningún order block con el 4H a favor en esa franja.")
    return ("bien" if bien else "mal"), explicacion


def texto(casos: list[Caso], res: Resultado) -> str:
    lineas = [f"Examen · {res.mercado.nombre}", ""]
    cuenta: dict = {}
    for caso in casos:
        estado, explicacion = examinar(caso, res)
        cuenta[estado] = cuenta.get(estado, 0) + 1
        cuando = f"{caso.desde:%d-%m-%Y %H:%M} a {caso.hasta:%d-%m-%Y %H:%M}" if caso.desde and caso.hasta else "sin fecha"
        lineas.append(f"[{estado.upper()}] {caso.id} · {cuando} · tenía que: {caso.esperado}")
        lineas.append(f"    {caso.fuente}: {caso.nota}")
        lineas += [f"    · {e}" for e in explicacion]
    resumen = " · ".join(f"{n} {estado}" for estado, n in sorted(cuenta.items()))
    lineas += ["", f"Resumen: {resumen}" if resumen else "No hay casos de este mercado."]
    return "\n".join(lineas)
