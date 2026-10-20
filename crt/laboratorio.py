"""Laboratorio: prueba cada regla candidata contra las reglas de hoy, en dos periodos.

Una regla candidata solo se propone si mejora la media de R por operación en los dos periodos (antes
y después de una fecha de corte) y deja suficientes operaciones para fiarse. El laboratorio nunca
cambia las reglas: propone. Las cambia el equipo, en ESTRATEGIA.md y en el código.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .motor import Ajustes, Operacion, Resultado, probar

MINIMO_OPERACIONES = 30

CANDIDATAS = (
    ("1 a 1 en vez de 1 a 2", {"ratio": 1.0}),
    ("Sin espera tras la apertura", {"espera_apertura_min": 0}),
    ("Espera de 30 min", {"espera_apertura_min": 30}),
    ("Espera de 60 min", {"espera_apertura_min": 60}),
    ("Solo después de la apertura", {"solo_tras_apertura": True}),
    ("Solo en Londres", {"solo_londres": True}),
    ("Diario: basta con que no vaya en contra", {"diario": "no_rojo"}),
    ("Stop a la entrada al llegar a +1 R", {"stop_a_entrada_en_r": 1.0}),
    ("Solo rangos con la vela 1 grande", {"vela1_minima": 1.0}),
    ("Sin el escenario 3", {"escenarios": ("1", "2", "otro")}),
    ("Como mucho 1 operación al día", {"max_operaciones_dia": 1}),
    ("No operar los días de noticias fuertes", {"sin_noticias": True}),
    # De los vídeos de los stops, de los 150.000 $, de la única vela y de psicología:
    ("Salir si se forma un rango de 1H en contra", {"salida_1h": "salir"}),
    ("Stop a la entrada si se forma un rango de 1H en contra", {"salida_1h": "entrada"}),
    ("TP en el objetivo del rango de 4H", {"tp_objetivo_4h": True}),
    ("Exigir el 1H a favor", {"exigir_1h": "verde"}),
    ("No entrar con el 1H en contra", {"exigir_1h": "no_rojo"}),
    ("Exigir el 3H a favor", {"exigir_3h": "verde"}),
    ("Solo situaciones sin banderas rojas", {"sin_banderas": True}),
    ("Dejar el día al perder 1 R (un stop)", {"perdida_max_dia_r": 1.0}),
    ("Un día de pausa tras 3 stops seguidos", {"pausa_tras_stops": 3}),
    ("Diario: rango aunque cierre un poco fuera", {"tolerancia_diario": 0.1}),
    ("Velas de 4H de futuros (empiezan a las 18:00)", {"inicio_4h": 18}),
    # Del vídeo de los 6.000 $:
    ("Diario: también vale tras una vela diaria expansiva a favor", {"diario": "expansiva"}),
    ("Salir en la zona de peligro (máximos nuevos de 4H y 1H y barrido en M15)", {"salida_peligro": True}),
)


def _stats(ops: list[Operacion]) -> dict:
    n = len(ops)
    total = sum(o.r for o in ops)
    return {"n": n, "total": total, "media": total / n if n else 0.0, "acierto": sum(1 for o in ops if o.r > 0) / n if n else 0.0}


def partir(res: Resultado, corte: datetime) -> tuple[dict, dict]:
    antes = [o for o in res.operaciones if o.hora_entrada < corte]
    despues = [o for o in res.operaciones if o.hora_entrada >= corte]
    return _stats(antes), _stats(despues)


def veredicto(base: tuple[dict, dict], candidata: tuple[dict, dict]) -> str:
    if min(candidata[0]["n"], candidata[1]["n"]) < MINIMO_OPERACIONES:
        return "pocas operaciones para saberlo"
    mejoras = [c["media"] > b["media"] for b, c in zip(base, candidata)]
    if all(mejoras):
        return "MEJORA en los dos periodos: proponer al equipo"
    if any(mejoras):
        return "dudosa: mejora solo en un periodo"
    return "no mejora"


@dataclass
class Prueba:
    nombre: str
    resultado: Resultado
    periodos: tuple[dict, dict]
    veredicto: str


def comprobar(barras, mercado, ajustes: Ajustes | None = None, noticias: dict | None = None, corte: datetime | None = None):
    """Devuelve (corte, base, [Prueba de cada candidata])."""
    ajustes = ajustes or Ajustes()
    if corte is None:  # por defecto, a dos tercios de los datos
        corte = barras[(len(barras) * 2) // 3].inicio
    base_res = probar(barras, mercado, ajustes, noticias)
    base = Prueba("Las reglas de hoy", base_res, partir(base_res, corte), "")
    pruebas = []
    for nombre, cambios in CANDIDATAS:
        if cambios.get("sin_noticias") and not noticias:
            continue
        res = probar(barras, mercado, replace(ajustes, **cambios), noticias)
        periodos = partir(res, corte)
        pruebas.append(Prueba(nombre, res, periodos, veredicto(base.periodos, periodos)))
    return corte, base, pruebas


def _r(x: float) -> str:
    return f"{x:+.2f} R".replace(".", ",")


def texto(corte: datetime, base: Prueba, pruebas: list[Prueba], hay_noticias: bool = True) -> str:
    fecha = f"{corte:%d-%m-%Y}"
    b1, b2 = base.periodos
    lineas = [
        f"Laboratorio: cada idea contra las reglas de hoy, antes y después del {fecha}",
        f"Reglas de hoy: antes {b1['n']} op. y media {_r(b1['media'])}; después {b2['n']} op. y media {_r(b2['media'])}.",
        f"Una idea solo se propone si mejora la media en los dos periodos con al menos {MINIMO_OPERACIONES} operaciones en cada uno.",
        "",
    ]
    for p in pruebas:
        c1, c2 = p.periodos
        lineas += [
            f"- {p.nombre}: {p.veredicto}",
            f"    antes:   {c1['n']:>4} op. · acierto {100 * c1['acierto']:>3.0f} % · media {_r(c1['media'])} · total {_r(c1['total'])}",
            f"    después: {c2['n']:>4} op. · acierto {100 * c2['acierto']:>3.0f} % · media {_r(c2['media'])} · total {_r(c2['total'])}",
        ]
    if not hay_noticias:
        lineas.append("- No operar los días de noticias fuertes: no se ha probado (faltan las noticias, ver --noticias).")
    return "\n".join(lineas)
