"""Prueba con datos del pasado: recorre las barras de M15 una a una y hace lo que haría el bot.

Nunca mira el futuro: en cada barra solo usa las velas ya cerradas y la vela en curso hasta ese
momento. Si en una misma barra se tocan el stop y el TP, cuenta como stop: no se sabe qué fue
primero y así la prueba no sale mejor de lo que es.

Además de operar, apunta en la memoria cada situación que ve: la primera vez que una idea de 4H da
un order block en horario (se tome o no, y por qué) y cada entrada. Las señales descartadas se siguen
como operaciones «fantasma» hasta su stop o su TP, para saber qué habría pasado: así se aprende qué
filtros ayudan y cuáles sobran.

En cada barra, por este orden:
  1. Si la barra empieza otra semana sin que la anterior cerrara (hueco en los datos), se cierra lo
     abierto donde se quedó el precio, y se cierran las velas que había.
  2. Se mira si algún rango ha llegado a su objetivo y se suma la barra a las velas en curso.
  3. Las operaciones abiertas (la real y las fantasma): ¿tocan el stop o el TP?
  4. Se cierran las velas que terminan con esta barra; pueden formar rangos nuevos. El viernes a las
     17:00 se cierra lo que quede abierto.
  5. Al cierre de la barra, para compras y para ventas: si hay order block con el 4H a favor, se
     comprueba todo lo demás (sesgo, diario, filtros, topes, stop y TP) y se decide.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time

from .entrada import es_order_block, hora_permitida, sesion
from .marcos import Marco, Setup
from .mercados import Mercado
from .rangos import semaforo
from .velas import QUINCE_MIN, Vela, dia_de_trading

STOP_MINIMO_EN_DIFERENCIALES = 3  # un stop más corto que esto no es realista: se lo comería el diferencial

# Decisiones. Los mismos textos en la memoria del Python y en la del bot de MT5.
ENTRADA = "entrada"
SIN_SESGO = "sin sesgo a favor"
DIARIO_EN_CONTRA = "el diario no está a favor"
YA_ABIERTA = "ya había una operación abierta"
ESCENARIO_NO_PERMITIDO = "escenario no permitido"
VELA1_PEQUENA = "vela 1 pequeña"
NOTICIAS = "día de noticias fuertes"
TOPE_DEL_DIA = "tope de operaciones del día"
PASO_EL_BARRIDO = "el precio ya pasó el barrido"
STOP_CORTO = "stop demasiado corto"
TP_NO_CABE = "el TP no cabe antes del objetivo del diario"


@dataclass
class Ajustes:
    ratio: float = 2.0  # el TP está a «ratio» veces lo que se arriesga
    espera_apertura_min: int = 45  # minutos sin entrar después de la apertura de las 9:30
    desde: time = time(1, 0)  # horario de entradas, en hora de Nueva York
    hasta: time = time(13, 0)
    solo_tras_apertura: bool = False
    solo_londres: bool = False
    diario: str = "verde"  # "verde": hace falta un rango diario a favor; "no_rojo": basta con que no vaya en contra; "ignorar": solo para pruebas
    comprobar_objetivo_diario: bool = True  # no entrar si el TP queda más allá del objetivo del diario
    max_operaciones_dia: int = 2  # por mercado
    # Reglas candidatas: apagadas hasta que el laboratorio demuestre que ayudan y el equipo las apruebe.
    stop_a_entrada_en_r: float | None = None  # al llegar a +X R, el stop pasa a la entrada
    vela1_minima: float | None = None  # el rango de 4H necesita una vela 1 de al menos X veces el tamaño medio
    escenarios: tuple | None = None  # escenarios permitidos (None: todos)
    sin_noticias: bool = False  # no entrar los días con noticias fuertes
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
    riesgo: float  # distancia de la entrada al stop inicial: 1 R
    tomada: bool = True  # False: operación fantasma (una señal descartada que se sigue para aprender)
    stop_en_entrada: bool = False
    hora_salida: datetime | None = None
    salida: float | None = None
    resultado: str = ""  # TP, SL, BE (stop en la entrada) o «Cierre semanal»
    r: float = 0.0  # resultado en R: +2 es un TP a 1 a 2, -1 un stop
    mfe_r: float = 0.0  # lo más que llegó a ir a favor, en R
    mae_r: float = 0.0  # lo más que llegó a ir en contra, en R

    @property
    def stop_inicial(self) -> float:
        return self.entrada - self.direccion * self.riesgo


@dataclass
class Senal:
    """Una situación que vio el bot (order block con el 4H a favor) y lo que decidió."""

    hora: datetime
    direccion: int
    decision: str
    sesion: str
    sesgo_semanal: int  # +1 a favor, 0 neutral, -1 en contra (respecto a la dirección de la señal)
    sesgo_mensual: int
    diario: str  # color del diario para esta dirección
    via_diario: str
    via_4h: str
    escenario: str
    vela1_rel: float | None
    stop_rel: float | None  # tamaño del stop comparado con el tamaño medio de las velas de 4H
    objetivo_r: float | None  # cuántos R hay hasta el objetivo del diario
    noticias: str
    operacion: Operacion | None = None


@dataclass
class Foto:
    """Cómo estaba el semáforo a una hora en punto; sirve para explicar lo que hizo el bot."""

    hora: datetime
    sesgo: int
    diario: dict  # {+1: color para compras, -1: color para ventas}
    h4: dict


@dataclass
class Resultado:
    mercado: Mercado
    ajustes: Ajustes
    operaciones: list[Operacion] = field(default_factory=list)  # las que se tomaron
    descartadas: Counter = field(default_factory=Counter)
    senales: list[Senal] = field(default_factory=list)  # la memoria
    fotos: list[Foto] = field(default_factory=list)
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


def probar(barras: list[Vela], mercado: Mercado, ajustes: Ajustes | None = None, noticias: dict | None = None) -> Resultado:
    """Hace la prueba con el pasado. «noticias» es {fecha de Nueva York: [nombres]} (ver noticias.py)."""
    recorrido = _Recorrido(mercado, ajustes or Ajustes(), noticias or {})
    for barra in barras:
        recorrido.paso(barra)
    return recorrido.terminar()


class _Recorrido:
    def __init__(self, mercado: Mercado, ajustes: Ajustes, noticias: dict):
        self.mercado, self.ajustes, self.noticias = mercado, ajustes, noticias
        self.h1 = Marco("H1")
        self.h4 = Marco("H4", menor=self.h1)
        self.d1 = Marco("D1", menor=self.h4)
        self.w1 = Marco("W1")
        self.mn = Marco("MN")
        self.marcos = (self.h1, self.h4, self.d1, self.w1, self.mn)
        self.res = Resultado(mercado, ajustes)
        self.abierta: Operacion | None = None
        self.fantasmas: list[Operacion] = []
        self.usados: set = set()  # ideas que ya dieron su entrada (o se descartaron al intentarla)
        self.vistos: set = set()  # ideas que ya están en la memoria
        self.por_dia: Counter = Counter()
        self.anterior: Vela | None = None

    def paso(self, barra: Vela) -> None:
        res, anterior = self.res, self.anterior
        if res.desde is None:
            res.desde = barra.inicio
        res.barras += 1

        # 1.
        if anterior is not None and self.w1.toca_cerrar_antes(barra):
            self._cerrar_todo(anterior.inicio + QUINCE_MIN, anterior.cierre)
        for m in self.marcos:
            if m.toca_cerrar_antes(barra):
                m.cerrar()

        # 2.
        for m in self.marcos:
            m.actualizar_con_barra(barra)
            m.sumar(barra)

        # 3.
        if self.abierta is not None and _revisar_salida(self.abierta, barra, self.mercado, self.ajustes):
            res.operaciones.append(self.abierta)
            self.abierta = None
        self.fantasmas = [op for op in self.fantasmas if not _revisar_salida(op, barra, self.mercado, self.ajustes)]

        # 4.
        fin_de_semana = self.w1.toca_cerrar_despues(barra)
        for m in self.marcos:
            if m.toca_cerrar_despues(barra):
                m.cerrar()
        hora = barra.inicio + QUINCE_MIN
        if fin_de_semana:
            self._cerrar_todo(hora, barra.cierre)
        if hora.minute == 0:
            self._foto(hora, barra.cierre)

        # 5.
        if anterior is not None and not fin_de_semana:
            for d in (+1, -1):
                self._mirar(barra, anterior, d)
        self.anterior = barra

    def terminar(self) -> Resultado:
        res = self.res
        if self.abierta is not None:
            res.descartadas["seguía abierta al acabar los datos"] += 1
        if self.anterior is not None:
            res.hasta = self.anterior.inicio + QUINCE_MIN
        return res

    # ───────────────────────── Decisión ─────────────────────────

    def _sesgo(self) -> int:
        return self.ajustes.sesgo_fijo if self.ajustes.sesgo_fijo is not None else sesgo_de_fondo(self.w1, self.mn)

    def _mirar(self, barra: Vela, anterior: Vela, d: int) -> None:
        a = self.ajustes
        hora = barra.inicio + QUINCE_MIN  # se entra al cierre de la barra
        if not hora_permitida(hora, a.desde, a.hasta, a.espera_apertura_min, a.solo_tras_apertura, a.solo_londres):
            return
        if not es_order_block(anterior, barra, d):
            return
        precio = barra.cierre
        setup = self.h4.setup(d, precio)
        if setup is None or barra.i_fin <= setup.i_inicio:
            return
        if any(i in self.usados for i in setup.ids):
            return  # esta idea ya dio su entrada: no hay nada nuevo

        # El diario: su color, si está a favor y dónde está su objetivo.
        diario = self.d1.setup(d, precio)
        color_diario = "verde" if diario is not None else semaforo(self.d1.ultimo, d)
        objetivo = diario.objetivo if diario is not None else None
        diario_vale = a.diario == "ignorar" or diario is not None
        if diario is None and a.diario == "no_rojo" and self.d1.cerradas and color_diario != "rojo":
            previa = self.d1.cerradas[-1]
            objetivo = previa.maximo if d > 0 else previa.minimo
            diario_vale = True
        if a.diario == "ignorar":
            objetivo = None

        niveles = _niveles(d, precio, setup, self.mercado, a.ratio)
        if self._sesgo() != d:
            decision = SIN_SESGO
        elif not diario_vale:
            decision = DIARIO_EN_CONTRA
        elif self.abierta is not None:
            decision = YA_ABIERTA
        else:
            self.usados.update(setup.ids)  # solo cuenta el primer order block de cada idea
            decision = self._filtros(setup, hora)
            if decision is None:
                if isinstance(niveles, str):
                    decision = niveles
                elif a.comprobar_objetivo_diario and not _cabe(d, niveles[3], objetivo, self.mercado):
                    decision = TP_NO_CABE
                else:
                    decision = ENTRADA

        nueva = not any(i in self.vistos for i in setup.ids)
        self.vistos.update(setup.ids)
        if not nueva and decision != ENTRADA:
            return

        operacion = None
        if not isinstance(niveles, str):
            entrada, stop, riesgo, tp = niveles
            operacion = Operacion(d, hora, sesion(hora), setup.escenario, setup.via, entrada, stop, tp, riesgo, tomada=decision == ENTRADA)
            if decision == ENTRADA:
                self.abierta = operacion
                self.por_dia[dia_de_trading(barra.inicio)] += 1
            else:
                self.fantasmas.append(operacion)
        if decision != ENTRADA:
            self.res.descartadas[decision] += 1
        self.res.senales.append(self._senal(hora, d, decision, color_diario, diario, setup, objetivo, operacion))

    def _filtros(self, setup: Setup, hora: datetime) -> str | None:
        a = self.ajustes
        if a.escenarios is not None and setup.escenario not in a.escenarios:
            return ESCENARIO_NO_PERMITIDO
        if a.vela1_minima is not None and (setup.vela1_rel is None or setup.vela1_rel < a.vela1_minima):
            return VELA1_PEQUENA
        if a.sin_noticias and self.noticias.get(hora.date()):
            return NOTICIAS
        if self.por_dia[dia_de_trading(hora - QUINCE_MIN)] >= a.max_operaciones_dia:
            return TOPE_DEL_DIA
        return None

    def _senal(self, hora, d, decision, color_diario, diario, setup, objetivo, op) -> Senal:
        medio = self.h4.rango_medio()
        stop_rel = op.riesgo / medio if op is not None and medio else None
        objetivo_r = (objetivo - op.entrada) * d / op.riesgo if op is not None and objetivo is not None else None
        return Senal(
            hora,
            d,
            decision,
            sesion(hora),
            direccion_de(self.w1.ultimo) * d,
            direccion_de(self.mn.ultimo) * d,
            color_diario,
            diario.via if diario is not None else "",
            setup.via,
            setup.escenario,
            setup.vela1_rel,
            stop_rel,
            objetivo_r,
            " | ".join(self.noticias.get(hora.date(), [])),
            op,
        )

    # ───────────────────────── Fotos y cierres ─────────────────────────

    def _foto(self, hora: datetime, precio: float) -> None:
        self.res.fotos.append(
            Foto(hora, self._sesgo(), {d: self.d1.color(d, precio) for d in (+1, -1)}, {d: self.h4.color(d, precio) for d in (+1, -1)})
        )

    def _cerrar_todo(self, hora: datetime, cierre: float) -> None:
        """Cierra lo abierto (la real y las fantasma) al precio de cierre: fin de semana o hueco."""
        for op in [self.abierta, *self.fantasmas]:
            if op is not None:
                _salir(op, hora, _precio_de_salida(op, cierre, self.mercado), "Cierre semanal")
        if self.abierta is not None:
            self.res.operaciones.append(self.abierta)
            self.abierta = None
        self.fantasmas = []


def _niveles(d: int, precio: float, setup: Setup, mercado: Mercado, ratio: float):
    """Entrada, stop, riesgo y TP, o el motivo por el que no se pueden poner."""
    if d > 0:
        if precio <= setup.barrido:
            return PASO_EL_BARRIDO
        entrada = precio + mercado.diferencial  # se compra al precio de compra
        stop = setup.barrido - mercado.colchon
        riesgo = entrada - stop
    else:
        if precio >= setup.barrido:
            return PASO_EL_BARRIDO
        entrada = precio
        stop = setup.barrido + mercado.colchon + mercado.diferencial  # las ventas se cierran comprando
        riesgo = stop - entrada
    if riesgo <= 0 or riesgo < STOP_MINIMO_EN_DIFERENCIALES * mercado.diferencial:
        return STOP_CORTO
    return entrada, stop, riesgo, entrada + d * ratio * riesgo


def _cabe(d: int, tp: float, objetivo: float | None, mercado: Mercado) -> bool:
    if objetivo is None:
        return True
    return tp <= objetivo if d > 0 else tp >= objetivo + mercado.diferencial


def _revisar_salida(op: Operacion, barra: Vela, mercado: Mercado, ajustes: Ajustes | None = None) -> bool:
    if op.direccion > 0:
        apertura, maximo, minimo = barra.apertura, barra.maximo, barra.minimo
        toca_stop, toca_tp = minimo <= op.stop, maximo >= op.tp
        salida_stop = min(op.stop, apertura)  # si abre más allá del stop, sale a la apertura
        a_favor, en_contra = (maximo - op.entrada) / op.riesgo, (op.entrada - minimo) / op.riesgo
    else:
        dif = mercado.diferencial  # una venta se cierra comprando, al precio de compra
        apertura, maximo, minimo = barra.apertura + dif, barra.maximo + dif, barra.minimo + dif
        toca_stop, toca_tp = maximo >= op.stop, minimo <= op.tp
        salida_stop = max(op.stop, apertura)
        a_favor, en_contra = (op.entrada - minimo) / op.riesgo, (maximo - op.entrada) / op.riesgo
    hora = barra.inicio + QUINCE_MIN
    op.mae_r = max(op.mae_r, en_contra)
    if toca_stop:  # si en la misma barra toca también el TP, cuenta el stop; lo que fue a favor no cuenta
        _salir(op, hora, salida_stop, "BE" if op.stop_en_entrada else "SL")
        return True
    op.mfe_r = max(op.mfe_r, a_favor)
    if toca_tp:
        _salir(op, hora, op.tp, "TP")
        return True
    if ajustes is not None and ajustes.stop_a_entrada_en_r and not op.stop_en_entrada and op.mfe_r >= ajustes.stop_a_entrada_en_r:
        op.stop, op.stop_en_entrada = op.entrada, True  # vale desde la barra siguiente
    return False


def _precio_de_salida(op: Operacion, cierre: float, mercado: Mercado) -> float:
    return cierre if op.direccion > 0 else cierre + mercado.diferencial


def _salir(op: Operacion, hora: datetime, precio: float, resultado: str) -> None:
    op.hora_salida, op.salida, op.resultado = hora, precio, resultado
    op.r = (precio - op.entrada) / op.riesgo * op.direccion
