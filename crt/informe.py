"""Resumen de una prueba con datos del pasado, en texto para leer."""

from __future__ import annotations

from .motor import Operacion, Resultado

NOMBRE_DIRECCION = {+1: "Compras", -1: "Ventas"}
NOMBRE_ESCENARIO = {"1": "Escenario 1", "2": "Escenario 2", "3": "Escenario 3", "otro": "Otros"}
NOMBRE_VIA = {"cierre": "Al cerrar la vela de 4H", "anticipo": "Antes, con 1H"}


def estadisticas(ops: list[Operacion]) -> dict:
    n = len(ops)
    total = sum(o.r for o in ops)
    pico = acumulado = caida = 0.0
    racha = peor_racha = 0
    for o in ops:
        acumulado += o.r
        pico = max(pico, acumulado)
        caida = max(caida, pico - acumulado)
        racha = racha + 1 if o.r < 0 else 0
        peor_racha = max(peor_racha, racha)
    ganadas = sum(1 for o in ops if o.r > 0)
    return {
        "n": n,
        "acierto": ganadas / n if n else 0.0,
        "total": total,
        "media": total / n if n else 0.0,
        "caida": caida,
        "racha": peor_racha,
    }


def _r(x: float) -> str:
    return f"{x:+.1f} R".replace(".", ",")


def _pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def _fecha(t) -> str:
    return t.strftime("%d-%m-%Y") if t else "—"


def _tabla(titulo: str, ops: list[Operacion], clave, nombres: dict | None = None) -> list[str]:
    grupos: dict = {}
    for o in ops:
        grupos.setdefault(clave(o), []).append(o)
    lineas = [titulo]
    for k in sorted(grupos, key=str):
        e = estadisticas(grupos[k])
        nombre = (nombres or {}).get(k, str(k))
        lineas.append(f"  {nombre:<26}{e['n']:>5} op. · acierto {_pct(e['acierto']):>5} · {_r(e['total']):>9}")
    return lineas


def texto(res: Resultado) -> str:
    a, ops = res.ajustes, res.operaciones
    lineas = [
        f"Prueba con datos del pasado · {res.mercado.nombre}",
        f"Datos: del {_fecha(res.desde)} al {_fecha(res.hasta)} ({res.barras} barras de 15 minutos)",
        f"Ajustes: objetivo 1 a {a.ratio:g} · espera tras la apertura {a.espera_apertura_min} min · "
        f"diario «{a.diario}» · entradas de {a.desde:%H:%M} a {a.hasta:%H:%M} de Nueva York"
        + (" · solo tras la apertura" if a.solo_tras_apertura else ""),
        "",
    ]
    if not ops:
        lineas.append("No ha salido ninguna operación.")
    else:
        e = estadisticas(ops)
        lineas += [
            f"Operaciones: {e['n']} · acierto {_pct(e['acierto'])} · resultado {_r(e['total'])} · "
            f"media {_r(e['media'])} por operación",
            f"Peor racha: {e['racha']} stops seguidos · peor caída: {_r(-e['caida'])}",
            f"Para no perder a 1 a {a.ratio:g} hay que acertar más del {100 / (1 + a.ratio):.0f} %.",
            "1 R es lo que se arriesga en cada operación (el 1 % de la cuenta).",
            "",
            *_tabla("Por sesión:", ops, lambda o: o.sesion),
            *_tabla("Por escenario:", ops, lambda o: o.escenario, NOMBRE_ESCENARIO),
            *_tabla("Por dirección:", ops, lambda o: o.direccion, NOMBRE_DIRECCION),
            *_tabla("Por cómo se puso en verde el 4H:", ops, lambda o: o.via, NOMBRE_VIA),
            *_tabla("Por año:", ops, lambda o: o.hora_entrada.year),
        ]
        cierres = sum(1 for o in ops if o.resultado == "Cierre semanal")
        if cierres:
            lineas.append(f"Cerradas el viernes sin tocar stop ni TP: {cierres}")
    if res.descartadas:
        lineas += ["", "Señales descartadas:"]
        lineas += [f"  {motivo}: {n}" for motivo, n in res.descartadas.most_common()]
    return "\n".join(lineas)


def linea_comparacion(nombre: str, res: Resultado, ancho: int = 55) -> str:
    e = estadisticas(res.operaciones)
    return (
        f"  {nombre:<{ancho}}{e['n']:>5} op. · acierto {_pct(e['acierto']):>5} · {_r(e['total']):>9} · "
        f"media {_r(e['media']):>7} · peor caída {_r(-e['caida']):>8}"
    )
