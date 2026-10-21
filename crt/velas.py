"""Velas de precio: leerlas de un CSV y agruparlas por marcos de tiempo.

Todo va en hora de Nueva York, con su cambio de hora. El día de trading empieza a las 17:00 de
Nueva York, como en MT5 y en el forex. Por eso las velas de 4H empiezan a las 17, 21, 1, 5, 9 y 13,
las mismas que usa el autor de la estrategia en el quinto vídeo («la vela de la 1 es Londres, la de
las 5 el London lunch y la de las 9 Nueva York»), y las de 3H a las 17, 20, 23, 2, 5, 8, 11 y 14 («la
de 3 horas de las 8» del vídeo de los 150.000 $).

En ese mismo vídeo la vela de 4H de la apertura es «la de las 6»: es lo que sale en el gráfico de
futuros de TradingView, cuyo día empieza a las 18:00 (velas de 4H a las 18, 22, 2, 6, 10 y 14). El
equipo decidió el 20-10-2026 las de las 17:00 en todos los mercados; la hora se puede cambiar (inicio_4h).

Las barras que caen en un día de trading de sábado o domingo (por ejemplo, las de los domingos antes de
la apertura de las 17:00 o las de los viernes después del cierre, que traen algunos datos) se quitan: si
no, formarían velas diarias y semanales falsas.

Las horas se guardan «de reloj» (sin zona), en hora de Nueva York. Para ordenar se usa siempre el
orden de llegada de las barras y nunca la hora: en el cambio de hora de otoño la 1:00 se repite.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NUEVA_YORK = ZoneInfo("America/New_York")
DESFASE_DIA = timedelta(hours=7)  # 17:00 de Nueva York + 7 h = 00:00 del día de trading
QUINCE_MIN = timedelta(minutes=15)


@dataclass
class Vela:
    inicio: datetime  # hora de Nueva York, de reloj
    apertura: float
    maximo: float
    minimo: float
    cierre: float
    i_inicio: int = 0  # primera barra de M15 de la vela
    i_fin: int = 0  # última barra de M15 de la vela

    @property
    def verde(self) -> bool:
        return self.cierre > self.apertura

    @property
    def roja(self) -> bool:
        return self.cierre < self.apertura

    @property
    def cuerpo(self) -> float:
        return abs(self.cierre - self.apertura)

    def sumar(self, barra: Vela) -> None:
        """Añade a la vela una barra posterior."""
        self.maximo = max(self.maximo, barra.maximo)
        self.minimo = min(self.minimo, barra.minimo)
        self.cierre = barra.cierre
        self.i_fin = barra.i_fin


def dia_de_trading(hora_ny: datetime) -> date:
    """Día al que pertenece una hora: va de las 17:00 a las 17:00 de Nueva York."""
    return (hora_ny + DESFASE_DIA).date()


def clave_y_fin(marco: str, inicio_ny: datetime, inicio_4h: int = 17) -> tuple[object, datetime]:
    """A qué vela del marco pertenece una barra que empieza a esta hora y a qué hora de Nueva York
    cierra esa vela. «inicio_4h» es la hora de Nueva York a la que empieza una vela de 4H."""
    t = inicio_ny + DESFASE_DIA
    if marco == "M15":
        clave = t.replace(minute=t.minute - t.minute % 15, second=0, microsecond=0)
        fin = clave + QUINCE_MIN
    elif marco == "H1":
        clave = t.replace(minute=0, second=0, microsecond=0)
        fin = clave + timedelta(hours=1)
    elif marco == "H3":
        clave = t.replace(hour=t.hour - t.hour % 3, minute=0, second=0, microsecond=0)
        fin = clave + timedelta(hours=3)
    elif marco == "H4":
        desfase = timedelta(hours=24 - inicio_4h)
        t = inicio_ny + desfase
        clave = t.replace(hour=t.hour - t.hour % 4, minute=0, second=0, microsecond=0)
        return clave, clave + timedelta(hours=4) - desfase
    elif marco == "D1":
        clave = datetime(t.year, t.month, t.day)
        fin = clave + timedelta(days=1)
    elif marco == "W1":
        clave = datetime(t.year, t.month, t.day) - timedelta(days=t.weekday())
        fin = clave + timedelta(days=5)  # sábado 00:00 de trading = viernes 17:00 de Nueva York
    elif marco == "MN":
        clave = datetime(t.year, t.month, 1)
        fin = datetime(t.year + (t.month == 12), t.month % 12 + 1, 1)
    else:
        raise ValueError(f"Marco desconocido: {marco}")
    return clave, fin - DESFASE_DIA


# ───────────────────────── Lectura de CSV ─────────────────────────

_COLUMNAS = {
    "apertura": ("open", "apertura", "o"),
    "maximo": ("high", "maximo", "máximo", "h"),
    "minimo": ("low", "minimo", "mínimo", "l"),
    "cierre": ("close", "cierre", "c"),
    "hora": ("timestamp", "datetime", "time", "date", "fecha", "hora", "gmt time", "local time"),
}


def _columna(cabecera: list[str], campo: str) -> int:
    for nombre in _COLUMNAS[campo]:
        if nombre in cabecera:
            return cabecera.index(nombre)
    raise ValueError(f"No encuentro la columna de {campo} en la cabecera: {cabecera}")


def _hora_utc(texto: str) -> datetime:
    t = texto.strip()
    if re.fullmatch(r"\d+(\.\d+)?", t):  # segundos o milisegundos desde 1970
        n = float(t)
        return datetime.fromtimestamp(n / 1000 if n > 1e11 else n, tz=timezone.utc)
    zona = re.search(r" GMT([+-])(\d{2}):?(\d{2})$", t)  # hora local de Dukascopy: «… GMT+0100»
    t = t[: zona.start()] if zona else t.split(" GMT")[0]
    t = t.replace("Z", "+00:00")
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})(.*)", t)  # 06.01.2025 14:30:00.000
    if m:
        t = f"{m[3]}-{m[2]}-{m[1]}{m[4]}"
    hora = datetime.fromisoformat(t.replace(".", "-", 2) if re.match(r"\d{4}\.", t) else t)
    if zona:
        desfase = timedelta(hours=int(zona[2]), minutes=int(zona[3])) * (1 if zona[1] == "+" else -1)
        return (hora - desfase).replace(tzinfo=timezone.utc)
    return hora if hora.tzinfo else hora.replace(tzinfo=timezone.utc)


def leer_csv(ruta: str, formato: str = "auto", desfase_servidor: int = 7) -> list[Vela]:
    """Lee precios de un CSV y los devuelve como barras de 15 minutos en hora de Nueva York.

    Formatos:
      - "mt5": lo que exporta MetaTrader 5 (Ver → Símbolos → Barras → Exportar barras): columnas
        <DATE>, <TIME>, <OPEN>, <HIGH>, <LOW> y <CLOSE>, en la hora del servidor del bróker. Casi
        todos los brókeres usan la hora de Nueva York + 7 (GMT+2 en invierno y GMT+3 en verano);
        si el vuestro usa otra, cambiad desfase_servidor.
      - "utc": una columna con la fecha y la hora en UTC y las columnas open, high, low y close.
      - "auto": lo decide por la cabecera.

    Sirven barras de 1 minuto o de 15 minutos: las de 1 minuto se juntan en barras de 15.
    """
    with open(ruta, newline="", encoding="utf-8-sig") as f:
        primera = f.readline()
        separador = "\t" if "\t" in primera else (";" if ";" in primera else ",")
        f.seek(0)
        lector = csv.reader(f, delimiter=separador)
        cabecera = [c.strip().strip("<>").lower() for c in next(lector)]
        # MT5 exporta la cabecera con corchetes: <DATE> <TIME>. Un CSV en UTC con «date» y «time» sin ellos no es de MT5.
        es_mt5 = formato == "mt5" or (formato == "auto" and "<date>" in primera.lower() and "time" in cabecera)
        ia, ih, il, ic = (_columna(cabecera, c) for c in ("apertura", "maximo", "minimo", "cierre"))
        filas = []
        if es_mt5:
            i_fecha, i_hora = cabecera.index("date"), cabecera.index("time")
            for fila in lector:
                if not fila:
                    continue
                servidor = datetime.fromisoformat(f"{fila[i_fecha].replace('.', '-')} {fila[i_hora]}")
                filas.append((servidor - timedelta(hours=desfase_servidor), fila[ia], fila[ih], fila[il], fila[ic]))
        else:
            if "date" in cabecera and "time" in cabecera and not {"datetime", "timestamp"} & set(cabecera):
                i_d, i_h = cabecera.index("date"), cabecera.index("time")  # la fecha y la hora en columnas separadas
                texto = lambda f: f"{f[i_d]} {f[i_h]}"
            else:
                i_t = _columna(cabecera, "hora")
                texto = lambda f: f[i_t]
            utc = [(_hora_utc(texto(f)), f[ia], f[ih], f[il], f[ic]) for f in lector if f]
            utc.sort(key=lambda x: x[0])
            filas = [(t.astimezone(NUEVA_YORK).replace(tzinfo=None), *resto) for t, *resto in utc]
    _comprobar_frecuencia(filas)
    filas = [f for f in filas if dia_de_trading(f[0]).weekday() < 5]  # fuera los días de trading de sábado y domingo
    return agrupar_en_m15(filas)


def _comprobar_frecuencia(filas) -> None:
    """Las velas de 1H se montan a partir de barras de 15 minutos: con barras más grandes no se puede.
    No cuentan los huecos de más de un día (fines de semana y festivos)."""
    minutos_entre = (int((b[0] - a[0]).total_seconds() // 60) for a, b in zip(filas[:500], filas[1:501]))
    saltos = Counter(m for m in minutos_entre if m <= 24 * 60)
    if saltos:
        minutos = saltos.most_common(1)[0][0]
        if minutos > 15:
            raise ValueError(f"El archivo tiene barras de {minutos} minutos: hacen falta barras de 1 o de 15 minutos.")


def agrupar_en_m15(filas) -> list[Vela]:
    """Junta filas (hora de Nueva York, apertura, máximo, mínimo, cierre) en barras de 15 minutos."""
    barras: list[Vela] = []
    clave_actual = None
    for hora, o, h, l, c in filas:
        o, h, l, c = float(o), float(h), float(l), float(c)
        clave, _ = clave_y_fin("M15", hora)
        if barras and clave == clave_actual:
            b = barras[-1]
            b.maximo, b.minimo, b.cierre = max(b.maximo, h), min(b.minimo, l), c
            continue
        clave_actual = clave
        i = len(barras)
        barras.append(Vela(clave - DESFASE_DIA, o, h, l, c, i, i))
    return barras
