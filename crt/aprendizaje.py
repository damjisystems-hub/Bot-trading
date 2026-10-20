"""Lo que enseña la memoria: qué situaciones ganan, cuáles pierden y qué habría pasado con las
señales descartadas.

Trabaja con las filas de la memoria (memoria.py), así que vale igual para la prueba con el pasado que
para lo que apunta el bot de MT5 en directo.

También saca lo que enseña el vídeo de psicología con números: los stops «buenos» (todo bien hecho y
salió mal), las rachas que son normales con el acierto que hay y si una operación influye en la
siguiente (no debería: cada una es independiente).
"""

from __future__ import annotations

import math

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


def _banderas(f: dict) -> list[str]:
    return [b for b in (f.get("banderas") or "").split(" | ") if b]


def racha_normal(n: int, acierto: float) -> int | None:
    """Los stops seguidos que es normal ver alguna vez en n operaciones con ese acierto (la racha más
    larga que se espera, aproximación de Schilling). None si hay muy pocas operaciones."""
    if n < 10 or not 0 < acierto < 1 or n * acierto <= 1:
        return None
    return round(math.log(n * acierto) / math.log(1 / (1 - acierto)))


def _psicologia(tomadas: list[dict]) -> list[str]:
    """Lo que dicen los números sobre las trampas del vídeo de psicología."""
    lineas = ["Psicología: lo que dicen los números"]
    tomadas = sorted(tomadas, key=lambda f: f["hora_ny"])
    rs = [_float(f["r"]) or 0.0 for f in tomadas]
    perdedoras = [f for f, r in zip(tomadas, rs) if r < 0]
    buenas = sum(1 for f in perdedoras if f.get("nota") == "A")
    if perdedoras:
        lineas.append(
            f"- Pérdidas «buenas» (nota A: sin banderas rojas): {buenas} de {len(perdedoras)} perdedoras. Se hizo todo bien y "
            "salió mal: son parte del juego y no son un motivo para cambiar las reglas."
        )
    suerte = sum(1 for f, r in zip(tomadas, rs) if r > 0 and f.get("nota") == "C")
    if suerte:
        lineas.append(
            f"- Ganadas con dos o más banderas rojas (nota C): {suerte}. Ganar así no demuestra que las banderas no importen: "
            "mirad el grupo entero, no una operación."
        )
    peor = racha = 0
    for r in rs:
        racha = racha + 1 if r < 0 else 0
        peor = max(peor, racha)
    e = estadisticas(tomadas)
    normal = racha_normal(e["n"], e["acierto"])
    linea = f"- Peor racha: {peor} stops seguidos."
    if normal is not None:
        linea += (
            f" Con un acierto del {100 * e['acierto']:.0f} %, en {e['n']} operaciones lo normal es ver alguna racha de unos "
            f"{normal} stops seguidos: es estadística, no que la estrategia haya dejado de funcionar."
        )
    lineas.append(linea)
    tras_tp = [r for previa, r in zip(rs, rs[1:]) if previa > 0]
    tras_stop = [r for previa, r in zip(rs, rs[1:]) if previa < 0]
    if tras_tp and tras_stop:
        def acierto(grupo: list[float]) -> str:
            aviso = "" if len(grupo) >= MINIMO_PARA_FIARSE else ", pocas"
            return f"{100 * sum(1 for r in grupo if r > 0) / len(grupo):.0f} % ({len(grupo)} op.{aviso})"

        lineas.append(
            f"- Tras una ganadora, la siguiente acertó el {acierto(tras_tp)}; tras un stop, el {acierto(tras_stop)}. "
            "Si se parecen, cada operación es independiente de la anterior: ni subir el riesgo tras ganar ni dejar de entrar tras perder."
        )
    return lineas


def _vela_4h(f: dict) -> str:
    """En qué vela de 4H fue la entrada («si ves que la vela de las nueve es la que se te da mejor…»)."""
    hora = f["hora_ny"][11:16]
    if hora <= "05:00":
        return "vela de la 1 (Londres)"
    if hora <= "09:00":
        return "vela de las 5"
    if hora <= "13:00":
        return "vela de las 9 (Nueva York)"
    return "más tarde"


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
            *_grupos("Por vela de 4H de la entrada (hora de Nueva York):", tomadas, _vela_4h),
            *_grupos("Por día de la semana:", tomadas, lambda f: f["dia_semana"]),
            *_grupos("Por escenario:", tomadas, lambda f: f["escenario"]),
            *_grupos("Por cómo se puso en verde el 4H:", tomadas, lambda f: f["via_4h"]),
            *_grupos("Por cómo se puso en verde el diario:", tomadas, lambda f: f["via_diario"] or "sin dato"),
            *_grupos("Por el 3H al entrar:", tomadas, lambda f: f.get("h3") or "sin dato"),
            *_grupos("Por el 1H al entrar:", tomadas, lambda f: f.get("h1") or "sin dato"),
            *_grupos("Por nota de la situación (A: sin banderas rojas; B: con una; C: con dos o más):", tomadas, lambda f: f.get("nota") or "sin dato"),
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
            "Por bandera roja (las operaciones que la llevaban; una operación puede llevar varias):",
            *[_linea(b, [f for f in tomadas if b in _banderas(f)]) for b in sorted({b for f in tomadas for b in _banderas(f)})],
            _linea("sin ninguna bandera", [f for f in tomadas if not _banderas(f)]),
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
        lineas += ["", *_psicologia(tomadas), ""]
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
