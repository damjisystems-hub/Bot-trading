"""Gatillo de entrada en M15 y horario en el que el bot puede entrar (hora de Nueva York)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

APERTURA_NY = time(9, 30)


def es_order_block(anterior, actual, direccion: int) -> bool:
    """Order block de M15 a favor. En compras: una vela roja y justo después una verde más fuerte,
    con el cuerpo más grande, que cierra por encima de donde abrió la roja. En ventas, al revés."""
    if actual.cuerpo <= anterior.cuerpo:
        return False
    if direccion > 0:
        return anterior.roja and actual.verde and actual.cierre > anterior.apertura
    return anterior.verde and actual.roja and actual.cierre < anterior.apertura


def fin_de_la_espera(espera_min: int) -> time:
    return (datetime.combine(date(2000, 1, 1), APERTURA_NY) + timedelta(minutes=espera_min)).time()


def hora_permitida(hora: datetime, desde: time, hasta: time, espera_min: int, solo_tras_apertura: bool) -> bool:
    """¿Puede entrar el bot al cierre de una barra que termina a esta hora?

    Entradas de «desde» a «hasta», y ninguna durante los primeros minutos tras la apertura de las
    9:30, que son muy agresivos (sexto vídeo)."""
    h = hora.time()
    if not desde < h <= hasta:
        return False
    if espera_min > 0 and APERTURA_NY < h < fin_de_la_espera(espera_min):
        return False
    return not (solo_tras_apertura and h <= APERTURA_NY)


def sesion(hora: datetime) -> str:
    return "Londres" if hora.time() <= APERTURA_NY else "Tras la apertura"
