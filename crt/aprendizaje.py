"""Lo que enseña la memoria: qué situaciones ganan, cuáles pierden y qué habría pasado con las
señales descartadas.

Trabaja con las filas de la memoria (memoria.py), así que vale igual para la prueba con el pasado que
para lo que apunta el bot de MT5 en directo.
"""

from __future__ import annotations

MINIMO_PARA_FIARSE = 30


def _float(texto: str) -> float | None:
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def estadisticas(filas: list[dict]) -> dict:
    rs = [_float(f["r"]) for f in filas]
    rs = [r for r in rs if r is not None]
    n = len(rs)
    total = sum(rs)
    return {"n": n, "acierto": sum(1 for r in rs if r > 0) / n if n else 0.0, "total": total, "media": total / n if n else 0.0}


def _r(x: float) -> str:
    return f"{x:+.1f} R".replace(".", ",")


def _linea(nombre: str, filas: list[dict]) -> str:
    e = estadisticas(filas)
    aviso = "" if e["n"] >= MINIMO_PARA_FIARSE else " (pocas)"
    return f"  {nombre:<30}{e['n']:>5} op. · acierto {100 * e['acierto']:>3.0f} % · {_r(e['total']):>9} · media {_r(e['media'])}{aviso}"


def _grupos(titulo: str, filas: list[dict], clave) -> list[str]:
    grupos: dict = {}
    for f in filas:
        grupos.setdefault(clave(f), []).append(f)
    return [titulo] + [_linea(k, grupos[k]) for k in sorted(grupos, key=str)]


def _tramo(texto: str, cortes: tuple, nombres: tuple, sin_dato: str = "sin dato") -> str:
    x = _float(texto)
    if x is None:
        return sin_dato
    for corte, nombre in zip(cortes, nombres):
        if x < corte:
            return nombre
    return nombres[-1]


def _franja(f: dict) -> str:
    hora = f["hora_ny"][11:16]
    if hora <= "05:00":
        return "1:00–5:00 (Londres)"
    if hora <= "09:30":
        return "5:00–9:30"
    return "tras la apertura"


def informe(filas: list[dict]) -> str:
    tomadas = [f for f in filas if f["tomada"] == "si" and f["r"]]
    descartadas = [f for f in filas if f["tomada"] == "no" and f["decision"] != "entrada"]
    lineas = [
        "Lo que enseña la memoria",
        f"Situaciones apuntadas: {len(filas)} · operaciones tomadas y cerradas: {len(tomadas)} · descartadas: {len(descartadas)}",
        f"Con menos de {MINIMO_PARA_FIARSE} operaciones en un grupo, las diferencias pueden ser casualidad: salen marcadas como «pocas».",
        "",
    ]
    if tomadas:
        lineas += [
            *_grupos("Por sesión:", tomadas, lambda f: f["sesion"]),
            *_grupos("Por franja horaria (Nueva York):", tomadas, _franja),
            *_grupos("Por día de la semana:", tomadas, lambda f: f["dia_semana"]),
            *_grupos("Por escenario:", tomadas, lambda f: f["escenario"]),
            *_grupos("Por cómo se puso en verde el 4H:", tomadas, lambda f: f["via_4h"]),
            *_grupos("Por cómo se puso en verde el diario:", tomadas, lambda f: f["via_diario"] or "sin dato"),
            *_grupos("Por sesgo mensual:", tomadas, lambda f: f["sesgo_mensual"]),
            *_grupos(
                "Por tamaño de la vela 1 del rango de 4H:",
                tomadas,
                lambda f: _tramo(f["vela1_rel"], (0.8, 1.25), ("pequeña", "normal", "grande")),
            ),
            *_grupos(
                "Por tamaño del stop:",
                tomadas,
                lambda f: _tramo(f["stop_rel"], (0.5, 1.0), ("corto", "normal", "largo")),
            ),
            *_grupos(
                "Por distancia al objetivo del diario:",
                tomadas,
                lambda f: _tramo(f["objetivo_r"], (3, 5), ("menos de 3 R", "de 3 a 5 R", "más de 5 R"), "sin objetivo"),
            ),
            *_grupos("Con o sin noticias fuertes ese día:", tomadas, lambda f: "con noticias" if f["noticias"] else "sin noticias"),
            "",
        ]
        stops = [f for f in tomadas if f["resultado"] in ("SL", "BE")]
        if stops:
            casi = sum(1 for f in stops if (_float(f["mfe_r"]) or 0) >= 1)
            lineas.append(
                f"De las {len(stops)} que acabaron en stop, {casi} ({100 * casi / len(stops):.0f} %) habían llegado antes a +1 R."
            )
        tps = [f for f in tomadas if f["resultado"] == "TP"]
        if tps:
            media_contra = sum(_float(f["mae_r"]) or 0 for f in tps) / len(tps)
            lineas.append(f"Las que llegaron al TP fueron antes de media {media_contra:.1f} R en contra.".replace(".", ",", 1))
        lineas.append("")
    if descartadas:
        lineas.append("Señales descartadas y lo que habría pasado si se hubieran tomado:")
        por_motivo: dict = {}
        for f in descartadas:
            por_motivo.setdefault(f["decision"], []).append(f)
        for motivo in sorted(por_motivo, key=lambda m: -len(por_motivo[m])):
            grupo = por_motivo[motivo]
            con_resultado = [f for f in grupo if f["r"]]
            if con_resultado:
                lineas.append(_linea(motivo, con_resultado) + f" · {len(grupo)} señales")
            else:
                lineas.append(f"  {motivo:<30}{len(grupo):>5} señales (sin niveles para seguirlas)")
        lineas.append("Si un motivo de descarte habría ganado dinero de forma clara, ese filtro sobra; si habría perdido, ayuda.")
    return "\n".join(lineas)
