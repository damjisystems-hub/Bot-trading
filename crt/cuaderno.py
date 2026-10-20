"""Cuaderno de operaciones: las que toma el equipo a mano y lo que le pasaba por la cabeza.

El vídeo de psicología dice que los días se califican por el proceso y no por el resultado, que ganar
saltándose el plan enseña al cerebro a repetirlo, que las rachas engañan y que hay que llevar la cuenta
de los propios errores. El bot no puede saber nada de eso: lo apunta el equipo en
cuaderno/operaciones.csv (se abre con Excel o Numbers) y este informe lo cuenta.

Columnas:
  fecha           AAAA-MM-DD o AAAA-MM-DD HH:MM (hora de Nueva York)
  mercado         nasdaq, eurusd u oro
  direccion       compra o venta
  cuenta          demo, propia o fondeo
  siguio_el_plan  si o no
  regla_rota      qué regla se saltó (vacío si se siguió el plan)
  emocion         cómo estabais: calma, dudas, miedo, prisa, venganza, euforia, avaricia, cansancio…
  resultado       TP, SL, BE o a mano
  r               resultado en R: 2, -1, 0, 0,5…
  nota            lo que queráis
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

COLUMNAS = ["fecha", "mercado", "direccion", "cuenta", "siguio_el_plan", "regla_rota", "emocion", "resultado", "r", "nota"]
CUENTAS = ("demo", "propia", "fondeo")
MAXIMO_OPERACIONES_DIA = 2  # por mercado, como el bot
TOPE_DE_PERDIDA_R = 3.0  # entre los tres mercados, como el bot
MESES_DE_DEMO_DEL_AUTOR = 6  # vídeo de «+100k al año»; en el del plan de 0 a 100.000 $ recomienda 3 (unas 60 sesiones)


@dataclass
class Apunte:
    fecha: datetime
    mercado: str
    direccion: str
    cuenta: str
    plan: bool
    regla_rota: str
    emocion: str
    resultado: str
    r: float
    nota: str


def _numero(texto: str, linea: int) -> float:
    try:
        return float(texto.strip().replace(",", ".").lstrip("+"))
    except ValueError:
        raise ValueError(f"Línea {linea}: «{texto}» no es un número de R (por ejemplo 2, -1 o 0,5)") from None


def leer(ruta: str) -> list[Apunte]:
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        lector = csv.DictReader(f)
        apuntes = []
        for linea, fila in enumerate(lector, start=2):
            fila = {k.strip().lower(): (v or "").strip() for k, v in fila.items() if k}
            if not any(fila.values()):
                continue
            plan = fila.get("siguio_el_plan", "").lower().replace("í", "i")
            if plan not in ("si", "no"):
                raise ValueError(f"Línea {linea}: siguio_el_plan tiene que ser «si» o «no»")
            cuenta = fila.get("cuenta", "").lower()
            if cuenta and cuenta not in CUENTAS:
                raise ValueError(f"Línea {linea}: la cuenta tiene que ser demo, propia o fondeo")
            try:
                fecha = datetime.fromisoformat(fila.get("fecha", ""))
            except ValueError:
                raise ValueError(f"Línea {linea}: la fecha tiene que ir así: 2026-10-20 o 2026-10-20 09:45") from None
            apuntes.append(Apunte(
                fecha, fila.get("mercado", "").lower(), fila.get("direccion", "").lower(), cuenta, plan == "si",
                fila.get("regla_rota", ""), fila.get("emocion", "").lower(), fila.get("resultado", ""),
                _numero(fila.get("r", ""), linea), fila.get("nota", ""),
            ))  # fmt: skip
    return sorted(apuntes, key=lambda a: a.fecha)


def _r(x: float) -> str:
    return f"{x:+.1f} R".replace(".", ",")


def _pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def _linea(nombre: str, grupo: list[Apunte]) -> str:
    n = len(grupo)
    total = sum(a.r for a in grupo)
    acierto = sum(1 for a in grupo if a.r > 0) / n
    return f"  {nombre:<28}{n:>4} op. · acierto {_pct(acierto):>5} · {_r(total):>8} · media {_r(total / n)}"


def _grupos(titulo: str, apuntes: list[Apunte], clave) -> list[str]:
    grupos: dict = {}
    for a in apuntes:
        grupos.setdefault(clave(a), []).append(a)
    return [titulo] + [_linea(k, grupos[k]) for k in sorted(grupos)]


def _meses(desde: datetime, hasta: datetime) -> str:
    return f"{(hasta - desde).days / 30.4:.1f}".replace(".", ",")


def informe(apuntes: list[Apunte]) -> str:
    if not apuntes:
        return "El cuaderno está vacío: apuntad cada operación que toméis (ver cuaderno/LEEME.md)."
    total = sum(a.r for a in apuntes)
    lineas = [
        f"Cuaderno de operaciones · {len(apuntes)} operaciones del {apuntes[0].fecha:%d-%m-%Y} al {apuntes[-1].fecha:%d-%m-%Y}",
        f"Resultado: {_r(total)} · acierto {_pct(sum(1 for a in apuntes if a.r > 0) / len(apuntes))} · "
        f"media {_r(total / len(apuntes))} por operación",
        "",
        *_grupos("Por cuenta:", apuntes, lambda a: a.cuenta or "sin decir"),
        *_grupos("Siguiendo el plan o no:", apuntes, lambda a: "siguiendo el plan" if a.plan else "saltándose el plan"),
        *_grupos("Por emoción:", apuntes, lambda a: a.emocion or "sin decir"),
        *_grupos("Por mercado:", apuntes, lambda a: a.mercado or "sin decir"),
    ]
    rotas = Counter(a.regla_rota.lower() for a in apuntes if not a.plan and a.regla_rota)
    if rotas:
        lineas.append("Reglas que más se saltan:")
        for regla, veces in rotas.most_common():
            grupo = [a for a in apuntes if not a.plan and a.regla_rota.lower() == regla]
            lineas.append(f"  {grupo[0].regla_rota:<40}{veces:>3} {'vez' if veces == 1 else 'veces'} · {_r(sum(a.r for a in grupo))}")
    lineas += ["", *_psicologia(apuntes), "", *_fases(apuntes)]
    return "\n".join(lineas)


def _psicologia(apuntes: list[Apunte]) -> list[str]:
    lineas = ["Psicología (vídeo de los 5 años de psicología):"]
    dias: dict = {}
    for a in apuntes:
        dias.setdefault(a.fecha.date(), []).append(a)
    bien = [d for d in dias.values() if all(a.plan for a in d)]
    mal = [d for d in dias.values() if not all(a.plan for a in d)]
    lineas.append(
        f"- Días bien hechos (todo siguiendo el plan): {len(bien)} de {len(dias)}, con {_r(sum(a.r for d in bien for a in d))}. "
        f"Días con algún fallo: {len(mal)}, con {_r(sum(a.r for d in mal for a in d))}. "
        "El día se califica por el proceso: uno bien hecho que pierde está bien; uno con fallos que gana, no."
    )
    ganadas_mal = sum(1 for a in apuntes if not a.plan and a.r > 0)
    if ganadas_mal:
        lineas.append(
            f"- Ganadas saltándose el plan: {ganadas_mal}. Son las más peligrosas, porque enseñan al cerebro a repetir el fallo. "
            "Cuentan como errores aunque hayan ganado."
        )
    perdidas_bien = sum(1 for a in apuntes if a.plan and a.r < 0)
    if perdidas_bien:
        lineas.append(f"- Perdidas siguiendo el plan: {perdidas_bien}. Son pérdidas buenas: no hay nada que cambiar por ellas.")
    tras_stop = [b for a, b in zip(apuntes, apuntes[1:]) if a.r < 0]
    resto = [b for a, b in zip(apuntes, apuntes[1:]) if a.r >= 0]
    if tras_stop and resto:
        lineas.append(
            f"- Después de una pérdida, la siguiente operación siguió el plan el {_pct(sum(a.plan for a in tras_stop) / len(tras_stop))} "
            f"de las veces; el resto del tiempo, el {_pct(sum(a.plan for a in resto) / len(resto))}. "
            "Si baja mucho después de perder, hay operaciones de venganza."
        )
    trampas = [a for a in apuntes if a.emocion in ("venganza", "euforia", "avaricia")]
    if trampas:
        lineas.append(
            f"- Con venganza, euforia o avaricia: {len(trampas)} operaciones, {_r(sum(a.r for a in trampas))}. La avaricia es "
            "alargar un objetivo ya cumplido («pequé de avaricia», vídeo de los 6.000 $)."
        )
    peor = racha = 0
    for a in apuntes:
        racha = racha + 1 if a.r < 0 else 0
        peor = max(peor, racha)
    lineas.append(f"- Peor racha: {peor} pérdidas seguidas. Cada operación es independiente de la anterior.")
    por_mercado = Counter((a.fecha.date(), a.mercado) for a in apuntes)
    demasiadas = sum(1 for n in por_mercado.values() if n > MAXIMO_OPERACIONES_DIA)
    if demasiadas:
        lineas.append(f"- Días con más de {MAXIMO_OPERACIONES_DIA} operaciones en un mercado: {demasiadas}. El plan dice {MAXIMO_OPERACIONES_DIA} como mucho.")
    pasados = sum(1 for d in dias.values() if sum(a.r for a in d) <= -TOPE_DE_PERDIDA_R)
    if pasados:
        lineas.append(
            f"- Días que se perdió {TOPE_DE_PERDIDA_R:g} R o más: {pasados}. Al llegar al tope, se cierra el gráfico hasta el día siguiente."
        )
    return lineas


def _fases(apuntes: list[Apunte]) -> list[str]:
    lineas = [
        f"Fases: primero demo, luego cuenta propia y después fondeo. Cuándo se pasa de una a otra lo decide el equipo; "
        f"el autor estuvo {MESES_DE_DEMO_DEL_AUTOR} meses en demo antes de pasar a cuentas de verdad y recomienda al menos 3 "
        "meses (unas 60 sesiones) haciéndolo todo bien y sin emociones."
    ]
    for cuenta in CUENTAS:
        grupo = [a for a in apuntes if a.cuenta == cuenta]
        if grupo:
            plan = sum(a.plan for a in grupo) / len(grupo)
            lineas.append(
                f"- {cuenta}: desde el {grupo[0].fecha:%d-%m-%Y}, {_meses(grupo[0].fecha, grupo[-1].fecha)} meses y "
                f"{len(grupo)} {'operación' if len(grupo) == 1 else 'operaciones'} "
                f"({_r(sum(a.r for a in grupo))}); siguiendo el plan el {_pct(plan)}."
            )
    return lineas
