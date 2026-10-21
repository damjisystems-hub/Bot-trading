"""Autoaprendizaje: el bot aprende solo de sus peores situaciones, con frenos para no aprender la suerte.

Decidido por el dueño el 21-10-2026: el bot aprende y se corrige solo con todo lo que le pasa. Cómo:

1. Repasa todo lo vivido: la prueba con el pasado sobre los precios que haya, que incluyen lo que hizo en directo
   si llegan hasta hoy (el bot de MT5 exporta los suyos cada día).
2. Busca sus peores situaciones: para cada cosa que describe una situación (sesión, vela de 4H, día, sesgo,
   diario, 3H, 1H, escenario, nota, cada bandera roja…; ver motor.ATRIBUTOS) y cada valor, cuánto ganan o pierden
   de media las operaciones que la tenían.
3. Cada una de las peores es una idea: «no entrar en esa situación». Se prueba con el bot entero y esa regla.
4. Frenos:
   - los datos se parten por fechas en tres tramos iguales; las peores se buscan solo en los dos primeros, y el
     tercero se guarda para confirmar;
   - una regla solo se aprende si mejora claramente (más que un «error típico», lo que baila la media por pura
     suerte) en los TRES tramos y deja al menos 30 operaciones en cada uno;
   - solo quita entradas: nunca añade riesgo;
   - cada vez se empieza de cero con los datos nuevos: lo que deja de cumplirse se desaprende.

Lo aprendido se escribe en reglas_aprendidas.txt, que leen el Python (Ajustes.vetos) y el bot de MT5.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from datetime import date, datetime

from . import memoria
from .laboratorio import MINIMO_OPERACIONES, _stats, error_tipico
from .mercados import Mercado
from .motor import ATRIBUTOS, Ajustes, Operacion, probar, vela_4h_de
from .velas import Vela

MINIMO_EN_GRUPO = 20  # operaciones con esa situación (en los dos primeros tramos) para tomarla en serio
MAXIMO_DE_IDEAS = 15  # las peores que se prueban en cada vuelta
ARCHIVO = "reglas_aprendidas.txt"
CABECERA = (
    "# Reglas aprendidas por el bot CRT (autoaprender.py). Solo quitan entradas: «no entrar si <atributo> es <valor>».\n"
    "# Se rehacen cada vez que el bot aprende: lo que deja de cumplirse, se quita.\n"
    "# mercado;atributo;valor;fecha;pruebas\n"
)


@dataclass
class Situacion:
    atributo: str
    valor: str
    n: int
    media: float  # media de R de las operaciones con esa situación (en los dos primeros tramos)
    total: float


@dataclass
class Prueba:
    situacion: Situacion
    base: tuple  # estadísticas de las reglas de hoy en los tres tramos
    con: tuple  # con la regla «no entrar en esa situación»
    aprendida: bool = False

    @property
    def veto(self) -> tuple:
        return (self.situacion.atributo, self.situacion.valor)


@dataclass
class Informe:
    mercado: Mercado
    cortes: tuple
    base: tuple
    peores: list
    pruebas: list = field(default_factory=list)
    aprendidas: list = field(default_factory=list)  # las reglas (atributo, valor) que se quedan
    juntas: tuple | None = None  # las aprendidas a la vez, en los tres tramos


def valores(fila: dict) -> dict:
    """Lo que describe la situación de una fila de la memoria (los mismos textos que motor._atributos)."""
    v = {a: fila.get(a, "") for a in ATRIBUTOS if a not in ("vela_4h", "bandera")}
    v["vela_4h"] = vela_4h_de(datetime.fromisoformat(fila["hora_ny"]))
    v["bandera"] = tuple(b for b in fila.get("banderas", "").split(" | ") if b)
    return v


def peores(filas: list[dict], minimo: int = MINIMO_EN_GRUPO) -> list[Situacion]:
    """Las situaciones de las operaciones tomadas, de la que más pierde a la que más gana (con al menos «minimo»)."""
    grupos: dict = {}
    for f in filas:
        if f.get("tomada") != "si" or not f.get("r"):
            continue
        r = float(f["r"])
        for atributo, valor in valores(f).items():
            for v in valor if atributo == "bandera" else (valor,):
                if v:
                    grupos.setdefault((atributo, v), []).append(r)
    lista = [Situacion(a, v, len(rs), sum(rs) / len(rs), sum(rs)) for (a, v), rs in grupos.items() if len(rs) >= minimo]
    return sorted(lista, key=lambda s: (s.media, s.total))


def cortes(barras: list[Vela]) -> tuple:
    """Las dos fechas que parten los datos en tres tramos iguales."""
    return barras[len(barras) // 3].inicio, barras[(2 * len(barras)) // 3].inicio


def tramos(ops: list[Operacion], c1: datetime, c2: datetime) -> tuple:
    return (
        _stats([o for o in ops if o.hora_entrada < c1]),
        _stats([o for o in ops if c1 <= o.hora_entrada < c2]),
        _stats([o for o in ops if o.hora_entrada >= c2]),
    )


def mejora_clara(base: dict, con: dict) -> bool:
    if con["n"] < MINIMO_OPERACIONES:
        return False
    return con["media"] - base["media"] > (error_tipico(base) ** 2 + error_tipico(con) ** 2) ** 0.5


def aprender(barras: list[Vela], mercado: Mercado, ajustes: Ajustes | None = None, noticias: dict | None = None) -> Informe:
    ajustes = replace(ajustes or Ajustes(), vetos=())  # se empieza de cero: lo aprendido antes se vuelve a probar
    c1, c2 = cortes(barras)
    res = probar(barras, mercado, ajustes, noticias)
    base = tramos(res.operaciones, c1, c2)
    filas = [f for f in memoria.filas(res) if datetime.fromisoformat(f["hora_ny"]) < c2]  # solo los dos primeros tramos
    tomadas = [float(f["r"]) for f in filas if f["tomada"] == "si" and f["r"]]
    media = sum(tomadas) / len(tomadas) if tomadas else 0.0
    lista = peores(filas)
    informe = Informe(mercado, (c1, c2), base, lista)
    for s in [s for s in lista if s.media < media][:MAXIMO_DE_IDEAS]:
        con = tramos(probar(barras, mercado, replace(ajustes, vetos=((s.atributo, s.valor),)), noticias).operaciones, c1, c2)
        prueba = Prueba(s, base, con, all(mejora_clara(b, c) for b, c in zip(base, con)))
        informe.pruebas.append(prueba)
    buenas = [p for p in informe.pruebas if p.aprendida]
    if len(buenas) > 1:  # todas a la vez también tienen que mejorar claramente; si no, se queda la mejor
        juntas = tramos(probar(barras, mercado, replace(ajustes, vetos=tuple(p.veto for p in buenas)), noticias).operaciones, c1, c2)
        if all(mejora_clara(b, c) for b, c in zip(base, juntas)):
            informe.juntas = juntas
        else:
            mejor = max(buenas, key=lambda p: p.con[2]["media"] - p.base[2]["media"])
            for p in buenas:
                p.aprendida = p is mejor
            buenas = [mejor]
    informe.aprendidas = [p.veto for p in buenas]
    return informe


# ───────────────────────── Texto ─────────────────────────


def _r(x: float) -> str:
    return f"{x:+.2f} R".replace(".", ",")


def _tramo(s: dict) -> str:
    return f"{s['n']} op., media {_r(s['media'])}"


def _situacion(atributo: str, valor: str) -> str:
    nombres = {
        "direccion": "la dirección es", "sesion": "la sesión es", "vela_4h": "la entrada es en la", "dia_semana": "el día es",
        "sesgo_semanal": "el sesgo semanal está", "sesgo_mensual": "el sesgo mensual está", "diario": "el diario está",
        "via_diario": "el diario se puso en verde por", "via_4h": "el 4H se puso en verde por", "h3": "el 3H está",
        "h1": "el 1H está", "escenario": "el escenario es", "nota": "la nota es", "bandera": "lleva la bandera",
    }  # fmt: skip
    return f"{nombres.get(atributo, atributo)} «{valor}»"


def texto(informe: Informe) -> str:
    c1, c2 = informe.cortes
    b = informe.base
    lineas = [
        f"Autoaprendizaje · {informe.mercado.nombre}",
        f"Tramos: hasta el {c1:%d-%m-%Y}, hasta el {c2:%d-%m-%Y} y después (este último solo para confirmar).",
        f"Reglas de hoy: {_tramo(b[0])} · {_tramo(b[1])} · {_tramo(b[2])}.",
        "",
        "Sus peores situaciones (en los dos primeros tramos, operaciones tomadas):",
    ]
    for s in informe.peores[:10]:
        lineas.append(f"  - {_situacion(s.atributo, s.valor)}: {s.n} op., media {_r(s.media)}, total {_r(s.total)}")
    if not informe.peores:
        lineas.append(f"  (ninguna con al menos {MINIMO_EN_GRUPO} operaciones todavía)")
    lineas += ["", "Lo que ha probado («no entrar si …»), en los tres tramos:"]
    for p in informe.pruebas:
        estado = "APRENDIDA" if p.aprendida else "no"
        tramos_ = " · ".join(f"{_r(bb['media'])} → {_r(cc['media'])} ({cc['n']} op.)" for bb, cc in zip(p.base, p.con))
        lineas.append(f"  - {estado}: {_situacion(*p.veto)}: {tramos_}")
    if not informe.pruebas:
        lineas.append("  (nada que probar)")
    lineas.append("")
    if informe.aprendidas:
        lineas.append("Aprendido: el bot dejará de entrar cuando " + "; cuando ".join(_situacion(*v) for v in informe.aprendidas) + ".")
        if informe.juntas:
            lineas.append(f"Todas a la vez: {_tramo(informe.juntas[0])} · {_tramo(informe.juntas[1])} · {_tramo(informe.juntas[2])}.")
    else:
        lineas.append(
            "No ha aprendido nada nuevo: ninguna idea mejora claramente en los tres tramos con al menos "
            f"{MINIMO_OPERACIONES} operaciones en cada uno. Con pocos datos es lo normal y es lo honesto: así no aprende la suerte."
        )
    lineas.append("Las cifras dependen de los datos y de los costes supuestos de cada mercado (crt/mercados.py).")
    return "\n".join(lineas)


# ───────────────────────── El archivo de reglas ─────────────────────────


def leer_reglas(ruta: str, mercado: str | None = None) -> list[tuple]:
    """[(mercado, atributo, valor)] del archivo (solo las de ese mercado, si se dice)."""
    if not os.path.exists(ruta):
        return []
    reglas = []
    with open(ruta, encoding="utf-8-sig") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            partes = linea.split(";")
            if len(partes) >= 3 and partes[1] in ATRIBUTOS and (mercado is None or partes[0] == mercado):
                reglas.append((partes[0], partes[1], partes[2]))
    return reglas


def vetos_de(ruta: str, mercado: str) -> tuple:
    """Los vetos de un mercado, listos para Ajustes(vetos=…)."""
    return tuple((a, v) for _, a, v in leer_reglas(ruta, mercado))


def escribir_reglas(ruta: str, informe: Informe, hoy: date | None = None) -> tuple[list, list]:
    """Cambia en el archivo las reglas de este mercado por las aprendidas ahora (las de otros mercados se quedan).
    Devuelve (nuevas, desaprendidas)."""
    nombre = informe.mercado.nombre
    hoy = hoy or date.today()
    antes = {(a, v) for _, a, v in leer_reglas(ruta, nombre)}
    otras = []
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8-sig") as f:
            otras = [l.rstrip("\n") for l in f if l.strip() and not l.startswith("#") and not l.startswith(nombre + ";")]
    pruebas = {p.veto: p for p in informe.pruebas}
    nuevas_lineas = []
    for veto in informe.aprendidas:
        p = pruebas[veto]
        evidencia = " · ".join(f"{_r(b['media'])} → {_r(c['media'])}" for b, c in zip(p.base, p.con))
        nuevas_lineas.append(f"{nombre};{veto[0]};{veto[1]};{hoy:%Y-%m-%d};media en los tres tramos: {evidencia}")
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(CABECERA)
        for linea in otras + nuevas_lineas:
            f.write(linea + "\n")
    ahora = set(informe.aprendidas)
    return sorted(ahora - antes), sorted(antes - ahora)
