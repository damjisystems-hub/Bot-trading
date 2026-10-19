"""Prueba con datos del pasado: recorre las barras de M15 una a una y hace lo que haría el bot.

Nunca mira el futuro: en cada barra solo usa las velas ya cerradas y la vela en curso hasta ese
momento. Si en una misma barra se tocan el stop y el TP, cuenta como stop: no se sabe qué fue
primero y así la prueba no sale mejor de lo que es.

En cada barra, por este orden:
  1. Si la barra empieza otra vela (lunes, o un hueco en los datos), se cierra la que había.
  2. Se mira si algún rango ha llegado a su objetivo y se suma la barra a las velas en curso.
  3. La operación abierta: ¿toca el stop o el TP?
  4. Se cierran las velas que terminan con esta barra; pueden formar rangos nuevos.
  5. Al cierre de la barra, ¿hay entrada? Horario, sesgo de fondo, order block de M15, diario a
     favor, semáforo de 4H en verde, stop, TP y topes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, time

from .entrada import es_order_block, hora_permitida, sesion
from .marcos import Marco
from .mercados import Mercado
from .velas import QUINCE_MIN, Vela, dia_de_trading

STOP_MINIMO_EN_DIFERENCIALES = 3  # un stop más corto que esto no es realista: se lo comería el diferencial


@dataclass
class Ajustes:
    ratio: float = 2.0  # el TP está a «ratio» veces lo que se arriesga
    espera_apertura_min: int = 45  # minutos sin entrar después de la apertura de las 9:30
    desde: time = time(1, 0)  # horario de entradas, en hora de Nueva York
    hasta: time = time(13, 0)
    solo_tras_apertura: bool = False
    diario: str = "verde"  # "verde": hace falta un rango diario a favor; "no_rojo": basta con que no vaya en contra; "ignorar": solo para pruebas
    comprobar_objetivo_diario: bool = True  # no entrar si el TP queda más allá del objetivo del diario
    max_operaciones_dia: int = 2  # por mercado
    sesgo_fijo: int | None = None  # solo para pruebas: +1 compras, -1 ventas


@dataclass
class Operacion:
    direccion: int  # +1 compra, -1 venta
    hora_entrada: datetime
    sesion: str
    escenario: str
    via: str
    entrada: float
    stop: float
    tp: float
    riesgo: float  # distancia de la entrada al stop: 1 R
    hora_salida: datetime | None = None
    salida: float | None = None
    resultado: str = ""  # TP, SL o «Cierre semanal»
    r: float = 0.0  # resultado en R: +2 es un TP a 1 a 2, -1 un stop


@dataclass
class Resultado:
    mercado: Mercado
    ajustes: Ajustes
    operaciones: list[Operacion] = field(default_factory=list)
    descartadas: Counter = field(default_factory=Counter)
    desde: datetime | None = None
    hasta: datetime | None = None
    barras: int = 0


def direccion_de(evento) -> int:
    """Hacia dónde empuja el último evento de un marco grande: un rango activo, hacia su objetivo;
    una ruptura, en su dirección. Un rango completado o anulado ya no empuja."""
    if evento is None:
        return 0
    if evento.tipo == "ruptura":
        return evento.direccion
    return evento.direccion if evento.estado == "activo" else 0


def sesgo_de_fondo(semanal: Marco, mensual: Marco) -> int:
    """Manda el semanal; si no dice nada, el mensual. Si se contradicen, no hay sesgo y no se opera."""
    s, m = direccion_de(semanal.ultimo), direccion_de(mensual.ultimo)
    if s == 0:
        return m
    return 0 if m == -s else s


def probar(barras: list[Vela], mercado: Mercado, ajustes: Ajustes | None = None) -> Resultado:
    ajustes = ajustes or Ajustes()
    h1 = Marco("H1")
    h4 = Marco("H4", menor=h1)
    d1 = Marco("D1", menor=h4)
    w1 = Marco("W1")
    mn = Marco("MN")
    marcos = (h1, h4, d1, w1, mn)
    res = Resultado(mercado, ajustes)
    abierta: Operacion | None = None
    usados: set = set()
    por_dia: Counter = Counter()
    anterior: Vela | None = None

    for barra in barras:
        if res.desde is None:
            res.desde = barra.inicio
        res.barras += 1

        # 1. Una semana nueva sin que la anterior cerrara en los datos: la operación se cierra donde
        #    se quedó el precio.
        if abierta is not None and anterior is not None and w1.toca_cerrar_antes(barra):
            _salir(abierta, anterior.inicio + QUINCE_MIN, _precio_de_salida(abierta, anterior.cierre, mercado), "Cierre semanal")
            res.operaciones.append(abierta)
            abierta = None
        for m in marcos:
            if m.toca_cerrar_antes(barra):
                m.cerrar()

        # 2.
        for m in marcos:
            m.actualizar_con_barra(barra)
            m.sumar(barra)

        # 3.
        if abierta is not None and _revisar_salida(abierta, barra, mercado):
            res.operaciones.append(abierta)
            abierta = None

        # 4. El viernes a las 17:00 se cierra lo que quede abierto.
        fin_de_semana = w1.toca_cerrar_despues(barra)
        for m in marcos:
            if m.toca_cerrar_despues(barra):
                m.cerrar()
        if abierta is not None and fin_de_semana:
            _salir(abierta, barra.inicio + QUINCE_MIN, _precio_de_salida(abierta, barra.cierre, mercado), "Cierre semanal")
            res.operaciones.append(abierta)
            abierta = None

        # 5.
        if abierta is None and anterior is not None and not fin_de_semana:
            abierta = _buscar_entrada(barra, anterior, h4, d1, w1, mn, mercado, ajustes, usados, por_dia, res.descartadas)

        anterior = barra

    if abierta is not None:
        res.descartadas["seguía abierta al acabar los datos"] += 1
    if anterior is not None:
        res.hasta = anterior.inicio + QUINCE_MIN
    return res


def _buscar_entrada(barra, anterior, h4, d1, w1, mn, mercado, ajustes, usados, por_dia, descartadas) -> Operacion | None:
    hora = barra.inicio + QUINCE_MIN  # se entra al cierre de la barra
    if not hora_permitida(hora, ajustes.desde, ajustes.hasta, ajustes.espera_apertura_min, ajustes.solo_tras_apertura):
        return None
    d = ajustes.sesgo_fijo if ajustes.sesgo_fijo is not None else sesgo_de_fondo(w1, mn)
    if d == 0 or not es_order_block(anterior, barra, d):
        return None
    precio = barra.cierre

    objetivo_diario = None
    if ajustes.diario != "ignorar":
        diario = d1.setup(d, precio)
        if diario is not None:
            objetivo_diario = diario.objetivo
        elif ajustes.diario == "no_rojo" and d1.cerradas and d1.color(d, precio) != "rojo":
            previa = d1.cerradas[-1]
            objetivo_diario = previa.maximo if d > 0 else previa.minimo
        else:
            return None

    setup = h4.setup(d, precio)
    if setup is None or barra.i_fin <= setup.i_inicio:
        return None
    if any(i in usados for i in setup.ids):
        return None
    usados.update(setup.ids)  # solo cuenta el primer order block de cada idea

    dia = dia_de_trading(barra.inicio)
    if por_dia[dia] >= ajustes.max_operaciones_dia:
        descartadas["tope de operaciones del día"] += 1
        return None
    if d > 0:
        if precio <= setup.barrido:
            return None
        entrada = precio + mercado.diferencial  # se compra al precio de compra
        stop = setup.barrido - mercado.colchon
        riesgo = entrada - stop
        tp = entrada + ajustes.ratio * riesgo
        cabe = objetivo_diario is None or tp <= objetivo_diario
    else:
        if precio >= setup.barrido:
            return None
        entrada = precio
        stop = setup.barrido + mercado.colchon + mercado.diferencial  # las ventas se cierran comprando
        riesgo = stop - entrada
        tp = entrada - ajustes.ratio * riesgo
        cabe = objetivo_diario is None or tp >= objetivo_diario + mercado.diferencial
    if riesgo <= 0 or riesgo < STOP_MINIMO_EN_DIFERENCIALES * mercado.diferencial:
        descartadas["stop demasiado corto"] += 1
        return None
    if ajustes.comprobar_objetivo_diario and not cabe:
        descartadas["el TP no cabe antes del objetivo del diario"] += 1
        return None
    por_dia[dia] += 1
    return Operacion(d, hora, sesion(hora), setup.escenario, setup.via, entrada, stop, tp, riesgo)


def _revisar_salida(op: Operacion, barra: Vela, mercado: Mercado) -> bool:
    if op.direccion > 0:
        apertura, maximo, minimo = barra.apertura, barra.maximo, barra.minimo
        toca_stop, toca_tp = minimo <= op.stop, maximo >= op.tp
        salida_stop = min(op.stop, apertura)  # si abre más allá del stop, sale a la apertura
    else:
        dif = mercado.diferencial  # una venta se cierra comprando, al precio de compra
        apertura, maximo, minimo = barra.apertura + dif, barra.maximo + dif, barra.minimo + dif
        toca_stop, toca_tp = maximo >= op.stop, minimo <= op.tp
        salida_stop = max(op.stop, apertura)
    hora = barra.inicio + QUINCE_MIN
    if toca_stop:
        _salir(op, hora, salida_stop, "SL")
        return True
    if toca_tp:
        _salir(op, hora, op.tp, "TP")
        return True
    return False


def _precio_de_salida(op: Operacion, cierre: float, mercado: Mercado) -> float:
    return cierre if op.direccion > 0 else cierre + mercado.diferencial


def _salir(op: Operacion, hora: datetime, precio: float, resultado: str) -> None:
    op.hora_salida, op.salida, op.resultado = hora, precio, resultado
    op.r = (precio - op.entrada) / op.riesgo * op.direccion
