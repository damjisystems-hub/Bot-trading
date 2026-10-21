"""Prueba con datos del pasado: recorre las barras de M15 una a una y hace lo que haría el bot.

Nunca mira el futuro: en cada barra solo usa las velas ya cerradas y la vela en curso hasta ese
momento. Si en una misma barra se tocan el stop y el TP, cuenta como stop: no se sabe qué fue
primero y así la prueba no sale mejor de lo que es.

Además de operar, apunta en la memoria cada situación que ve: la primera vez que una idea de 4H da
un order block en horario (se tome o no, y por qué) y cada entrada. Las señales descartadas se siguen
como operaciones «fantasma» hasta su stop o su TP, para saber qué habría pasado: así se aprende qué
filtros ayudan y cuáles sobran. Cada situación lleva sus «banderas rojas» (lo que el autor no quiere
ver al entrar) y una nota: A sin banderas, B con una y C con dos o más.

En cada barra, por este orden:
  1. Si la barra empieza otra semana sin que la anterior cerrara (hueco en los datos), se cierra lo
     abierto donde se quedó el precio, y se cierran las velas que había.
  2. Se mira si algún rango ha llegado a su objetivo y se suma la barra a las velas en curso.
  3. Las operaciones abiertas (la real y las fantasma): ¿tocan el stop o el TP? Con la regla candidata
     de la zona de peligro, también pueden salir al cierre de la barra.
  4. Se cierran las velas que terminan con esta barra; pueden formar rangos nuevos. Con la regla
     candidata de salida por 1H, un rango de 1H en contra cierra la operación (o lleva el stop a la
     entrada). El viernes a las 17:00 se cierra lo que quede abierto.
  5. Al cierre de la barra, para compras y para ventas: si hay order block con el 4H a favor, se
     comprueba todo lo demás (sesgo, diario, filtros, topes, stop y TP) y se decide.
"""

from __future__ import annotations

import heapq
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from .entrada import APERTURA_NY, es_order_block, hora_permitida, sesion
from .marcos import Marco, Setup
from .mercados import Mercado
from .rangos import evaluar, semaforo
from .velas import QUINCE_MIN, Vela, dia_de_trading

STOP_MINIMO_EN_DIFERENCIALES = 3  # un stop más corto que esto no es realista: se lo comería el diferencial
MINIMO_R_OBJETIVO = 1.0  # con el TP en el objetivo del 4H, no se entra si está a menos de esto

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
TP_NO_CABE_4H = "el TP no cabe antes del objetivo del 4H"
H3_NO_ACOMPANA = "el 3H no acompaña"
H1_NO_ACOMPANA = "el 1H no acompaña"
CON_BANDERAS = "situación con banderas rojas"
OBJETIVO_CERCA = "el objetivo del 4H está a menos de 1 R"
PAUSA = "pausa tras una racha de stops"
TOPE_DE_PERDIDA = "tope de pérdida del día"
LEJOS = "la entrada queda lejos del barrido"
AL_OTRO_LADO = "al otro lado de la apertura del día"
ANTES_DE_NOTICIAS = "antes de una noticia fuerte"
DECISIONES = (
    ENTRADA, SIN_SESGO, DIARIO_EN_CONTRA, YA_ABIERTA, ESCENARIO_NO_PERMITIDO, VELA1_PEQUENA, NOTICIAS,
    TOPE_DEL_DIA, PASO_EL_BARRIDO, STOP_CORTO, TP_NO_CABE, H3_NO_ACOMPANA, H1_NO_ACOMPANA, CON_BANDERAS,
    OBJETIVO_CERCA, PAUSA, TOPE_DE_PERDIDA, LEJOS, AL_OTRO_LADO, ANTES_DE_NOTICIAS, TP_NO_CABE_4H,
)  # fmt: skip

# Cómo termina una operación.
CIERRE_SEMANAL = "Cierre semanal"
SALIDA_1H = "Salida por 1H"
ZONA_DE_PELIGRO = "Zona de peligro"
CIERRE_DEL_DIA = "Cierre del día"
SALIDA_POR_TIEMPO = "Salida por tiempo"
RESULTADOS = ("TP", "SL", "BE", CIERRE_SEMANAL, SALIDA_1H, ZONA_DE_PELIGRO, CIERRE_DEL_DIA, SALIDA_POR_TIEMPO)

# Banderas rojas: lo que el autor no quiere ver al entrar (vídeos de los stops, de los 150.000 $ y de la
# única vela). No impiden entrar: se apuntan para ver si las que las llevan pierden más.
B_DIARIO_EN_CONTRA = "el diario va en contra"  # el diario solo está en verde anticipado y lo cerrado va en contra
B_DIARIO_TOMANDO = {+1: "el diario está tomando máximos", -1: "el diario está tomando mínimos"}
B_4H_TOMANDO = {+1: "el 4H está tomando máximos", -1: "el 4H está tomando mínimos"}
B_1H_TOMANDO = {+1: "el 1H está tomando máximos", -1: "el 1H está tomando mínimos"}  # «la nueva vela de 1H abre por arriba: otra red flag»
B_3H_EN_CONTRA = "el 3H va en contra"
B_1H_EN_CONTRA = "el 1H va en contra"
# «Si buscas compras, debajo de la apertura de cada vela es el punto ideal»; «vender por encima de la apertura diaria».
B_APERTURA_DEL_DIA = {+1: "compra por encima de la apertura del día", -1: "venta por debajo de la apertura del día"}
B_ANTES_DE_LA_APERTURA = "justo antes de la apertura"  # de 9:00 a 9:30
B_LEJOS_DEL_BARRIDO = "entrada lejos del barrido"  # stop más grande que una vela media de 4H: si falla, stop directo
BANDERAS = (
    B_DIARIO_EN_CONTRA, *B_DIARIO_TOMANDO.values(), *B_4H_TOMANDO.values(), *B_1H_TOMANDO.values(), B_3H_EN_CONTRA,
    B_1H_EN_CONTRA, *B_APERTURA_DEL_DIA.values(), B_ANTES_DE_LA_APERTURA, B_LEJOS_DEL_BARRIDO,
)  # fmt: skip
MEDIA_HORA_ANTES = time(9, 0)
VELA_DE_LAS_9 = time(9, 0)


@dataclass
class Ajustes:
    ratio: float = 2.0  # el TP está a «ratio» veces lo que se arriesga
    espera_apertura_min: int = 45  # minutos sin entrar después de la apertura de las 9:30
    desde: time = time(1, 0)  # horario de entradas, en hora de Nueva York
    hasta: time = time(13, 0)
    solo_tras_apertura: bool = False
    solo_londres: bool = False
    diario: str = "verde"  # "verde": hace falta un rango diario a favor; "no_rojo": basta con que no vaya en contra; "expansiva": también vale tras una vela diaria expansiva a favor; "ignorar": solo para pruebas
    comprobar_objetivo_diario: bool = True  # no entrar si el TP queda más allá del objetivo del diario
    max_operaciones_dia: int = 2  # por mercado
    perdida_max_dia_r: float | None = 3.0  # al perder tanto en un día (en R) no se entra más ese día; en MT5 suma todos los mercados, aquí solo este
    inicio_4h: int = 17  # hora de Nueva York a la que empiezan las velas de 4H: 17 (las de la 1, las 5 y las 9), lo decidido el 20-10-2026
    # Reglas candidatas: apagadas hasta que el laboratorio demuestre que ayudan y el equipo las apruebe.
    stop_a_entrada_en_r: float | None = None  # al llegar a +X R, el stop pasa a la entrada
    vela1_minima: float | None = None  # el rango de 4H necesita una vela 1 de al menos X veces el tamaño medio
    escenarios: tuple | None = None  # escenarios permitidos (None: todos)
    sin_noticias: bool = False  # no entrar los días con noticias fuertes
    salida_1h: str | None = None  # si se forma un rango de 1H en contra: "salir" o "entrada" (stop a la entrada si va ganando; si no, salir)
    salida_peligro: bool = False  # salir en la zona de peligro: ganando, 4H y 1H en máximos nuevos y un barrido en contra en M15
    tp_hasta_objetivo_4h: bool = False  # si el objetivo del 4H está más lejos que el TP, dejar correr hasta él
    no_perseguir: bool = False  # si la entrada queda lejos del barrido, no entrar y esperar otro order block de la misma idea
    apertura_del_dia: bool = False  # comprar solo por debajo de la apertura del día y vender solo por encima
    antes_de_noticias: bool = False  # no entrar antes de la primera noticia fuerte del día
    cierre_diario: bool = False  # cerrar lo abierto al final de cada día (17:00), como en las cuentas de futuros
    salida_por_tiempo: bool = False  # ganando, salir cuando una vela de 4H nueva supera el extremo de la anterior a favor
    be_antes_de_las_9: bool = False  # ganando, stop a la entrada justo antes de que abra la vela de 4H de las 9:00
    comprobar_objetivo_4h: bool = False  # no entrar si el TP queda más allá del objetivo del rango de 4H
    ignorar_sesgo: bool = False  # sin sesgo de fondo (con diario="ignorar", el modelo del backtest del autor)
    vetar_tomando: bool = False  # no entrar con el diario o el 4H tomando máximos (compras) o mínimos (ventas)
    tp_objetivo_4h: bool = False  # TP en el objetivo del rango de 4H en vez de a «ratio» veces el riesgo
    exigir_1h: str | None = None  # el 1H tiene que estar "verde" (rango a favor) o "no_rojo" (no en contra)
    exigir_3h: str | None = None  # lo mismo con el 3H
    sin_banderas: bool = False  # solo situaciones sin banderas rojas (nota A)
    max_banderas: int | None = None  # como mucho tantas banderas rojas (1: nota A o B)
    pausa_tras_stops: int | None = None  # tras tantos stops seguidos, el resto del día y el siguiente sin operar
    tolerancia_diario: float = 0.0  # un rango diario que cierra hasta esta parte de la vela 1 por fuera sigue contando
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
    resultado: str = ""  # uno de RESULTADOS: TP, SL, BE (stop en la entrada), los cierres y las salidas candidatas
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
    h3: str = ""  # color del 3H para esta dirección
    h1: str = ""  # color del 1H para esta dirección
    banderas: tuple = ()

    @property
    def nota(self) -> str:
        """A: sin banderas rojas; B: con una; C: con dos o más."""
        return "ABC"[min(len(self.banderas), 2)]


@dataclass
class Foto:
    """Cómo estaba el semáforo a una hora en punto; sirve para explicar lo que hizo el bot."""

    hora: datetime
    sesgo: int
    diario: dict  # {+1: color para compras, -1: color para ventas}
    h4: dict
    h1: dict = field(default_factory=dict)


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


def probar_cartera(mercados: dict, ajustes: Ajustes | None = None, noticias: dict | None = None) -> dict:
    """Prueba varios mercados a la vez, barra a barra por orden de hora, con el tope de pérdida del día sumando
    lo de todos, como el bot de MT5 en directo. «mercados» es {nombre: (barras, Mercado)} y «noticias»,
    {nombre: {fecha: [noticias]}}. Devuelve {nombre: Resultado}."""
    comun: defaultdict = defaultdict(float)  # el resultado de cada día, entre todos los mercados
    recorridos = {}
    for nombre, (_, mercado) in mercados.items():
        recorridos[nombre] = _Recorrido(mercado, ajustes or Ajustes(), (noticias or {}).get(nombre, {}))
        recorridos[nombre].r_por_dia = comun
    def flujo(i: int, nombre: str, barras: list):
        return ((b.inicio, i, nombre, b) for b in barras)

    flujos = [flujo(i, nombre, barras) for i, (nombre, (barras, _)) in enumerate(mercados.items())]
    for _, _, nombre, barra in heapq.merge(*flujos, key=lambda x: (x[0], x[1])):
        recorridos[nombre].paso(barra)
    return {nombre: r.terminar() for nombre, r in recorridos.items()}


class _Recorrido:
    def __init__(self, mercado: Mercado, ajustes: Ajustes, noticias: dict):
        self.mercado, self.ajustes, self.noticias = mercado, ajustes, noticias
        self.h1 = Marco("H1")
        self.h3 = Marco("H3")
        self.h4 = Marco("H4", menor=self.h1, inicio_4h=ajustes.inicio_4h)
        self.d1 = Marco("D1", menor=self.h4, tolerancia=ajustes.tolerancia_diario)
        self.w1 = Marco("W1")
        self.mn = Marco("MN")
        self.marcos = (self.h1, self.h3, self.h4, self.d1, self.w1, self.mn)
        self.res = Resultado(mercado, ajustes)
        self.abierta: Operacion | None = None
        self.fantasmas: list[Operacion] = []
        self.usados: set = set()  # ideas que ya dieron su entrada (o se descartaron al intentarla)
        self.vistos: set = set()  # ideas que ya están en la memoria
        self.por_dia: Counter = Counter()
        self.r_por_dia: defaultdict = defaultdict(float)  # resultado de las operaciones cerradas cada día
        self.racha = 0  # stops seguidos de las operaciones tomadas
        self.pausa_hasta: date | None = None
        self.anterior: Vela | None = None

    def paso(self, barra: Vela) -> None:
        res, anterior = self.res, self.anterior
        if res.desde is None:
            res.desde = barra.inicio
        res.barras += 1

        # 1.
        if anterior is not None and self.w1.toca_cerrar_antes(barra):
            self._cerrar_todo(anterior.inicio + QUINCE_MIN, anterior.cierre)
        if anterior is not None and self.ajustes.cierre_diario and self.d1.toca_cerrar_antes(barra):
            self._cerrar_todo(anterior.inicio + QUINCE_MIN, anterior.cierre, CIERRE_DEL_DIA)
        for m in self.marcos:
            if m.toca_cerrar_antes(barra):
                self._cerrar(m, anterior.inicio + QUINCE_MIN, anterior.cierre)

        # 2.
        for m in self.marcos:
            m.actualizar_con_barra(barra)
            m.sumar(barra)

        # 3.
        if self.abierta is not None and self._sale(self.abierta, barra, anterior):
            self._cerrada(self.abierta)
        self.fantasmas = [op for op in self.fantasmas if not self._sale(op, barra, anterior)]

        # 4.
        hora = barra.inicio + QUINCE_MIN
        fin_de_semana = self.w1.toca_cerrar_despues(barra)
        fin_del_dia = self.d1.toca_cerrar_despues(barra)
        for m in self.marcos:
            if m.toca_cerrar_despues(barra):
                self._cerrar(m, hora, barra.cierre)
        if fin_de_semana:
            self._cerrar_todo(hora, barra.cierre)
        elif fin_del_dia and self.ajustes.cierre_diario:
            self._cerrar_todo(hora, barra.cierre, CIERRE_DEL_DIA)
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
        if setup is not None and setup.via == "cierre" and any(i in self.usados for i in setup.ids):
            # La idea de 4H ya dio su entrada. Si la vela en curso está formando otro rango a favor (por
            # ejemplo, tras barrer el stop), es una idea nueva: «me saca, reacciona, vuelve a hacer un
            # rango de 4H y un order block… y vuelvo a entrar» (vídeo de los stops).
            setup = self.h4.anticipo(d, precio)
        if setup is None or barra.i_fin <= setup.i_inicio:
            return
        if any(i in self.usados for i in setup.ids):
            return  # esta idea ya dio su entrada: no hay nada nuevo

        # El diario: su color, si está a favor y dónde está su objetivo.
        diario = self.d1.setup(d, precio)
        color_diario = "verde" if diario is not None else semaforo(self.d1.ultimo, d)
        objetivo = diario.objetivo if diario is not None else None
        diario_vale = a.diario == "ignorar" or diario is not None
        ultimo = self.d1.ultimo
        expansiva = ultimo is not None and ultimo.tipo == "ruptura" and ultimo.direccion == d
        if diario is None and self.d1.cerradas and (
            (a.diario == "no_rojo" and color_diario != "rojo") or (a.diario == "expansiva" and expansiva)
        ):
            # «Una vela expansiva alcista: es muy probable que vayamos a tomar el máximo del día anterior»
            # (vídeo de los 6.000 $): el objetivo es el extremo de la vela diaria anterior.
            previa = self.d1.cerradas[-1]
            objetivo = previa.maximo if d > 0 else previa.minimo
            diario_vale = True
        if a.diario == "ignorar":
            objetivo = None

        niveles = _niveles(d, precio, setup, self.mercado, a.ratio, a.tp_objetivo_4h, a.tp_hasta_objetivo_4h)
        colores = {"h3": self.h3.color(d, precio), "h1": self.h1.color(d, precio)}
        banderas = self._banderas(d, hora, precio, colores, niveles)
        if not a.ignorar_sesgo and self._sesgo() != d:
            decision = SIN_SESGO
        elif not diario_vale:
            decision = DIARIO_EN_CONTRA
        elif self.abierta is not None:
            decision = YA_ABIERTA
        elif a.no_perseguir and B_LEJOS_DEL_BARRIDO in banderas:
            # «Nunca entréis persiguiendo el precio cuando está tan lejos»: la idea no se gasta y se espera otro
            # order block más cerca del barrido (vídeo de las pruebas de fondeo).
            decision = LEJOS
        else:
            self.usados.update(setup.ids)  # solo cuenta el primer order block de cada idea
            decision = self._filtros(setup, hora, colores, banderas)
            if decision is None:
                if isinstance(niveles, str):
                    decision = niveles
                elif a.comprobar_objetivo_4h and not _cabe(d, niveles[3], setup.objetivo, self.mercado):
                    decision = TP_NO_CABE_4H  # «no vamos a querer tomar un trade de ratio uno»
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
        self.res.senales.append(self._senal(hora, d, decision, color_diario, diario, setup, objetivo, operacion, colores, banderas))

    def _banderas(self, d: int, hora: datetime, precio: float, colores: dict, niveles) -> tuple:
        """Las banderas rojas de esta situación (ver BANDERAS), en ese orden."""
        banderas = []
        if semaforo(self.d1.ultimo, d) == "rojo":
            banderas.append(B_DIARIO_EN_CONTRA)
        if self.d1.tomando(d):
            banderas.append(B_DIARIO_TOMANDO[d])
        if self.h4.tomando(d):
            banderas.append(B_4H_TOMANDO[d])
        if self.h1.tomando(d):
            banderas.append(B_1H_TOMANDO[d])
        if colores["h3"] == "rojo":
            banderas.append(B_3H_EN_CONTRA)
        if colores["h1"] == "rojo":
            banderas.append(B_1H_EN_CONTRA)
        if self.d1.parcial is not None and (precio - self.d1.parcial.apertura) * d > 0:
            banderas.append(B_APERTURA_DEL_DIA[d])
        if MEDIA_HORA_ANTES < hora.time() <= APERTURA_NY:
            banderas.append(B_ANTES_DE_LA_APERTURA)
        medio = self.h4.rango_medio()
        if not isinstance(niveles, str) and medio and niveles[2] > medio:
            banderas.append(B_LEJOS_DEL_BARRIDO)
        return tuple(banderas)

    def _filtros(self, setup: Setup, hora: datetime, colores: dict, banderas: tuple) -> str | None:
        a = self.ajustes
        dia = dia_de_trading(hora - QUINCE_MIN)
        if a.escenarios is not None and setup.escenario not in a.escenarios:
            return ESCENARIO_NO_PERMITIDO
        if a.vela1_minima and (setup.vela1_rel is None or setup.vela1_rel < a.vela1_minima):  # 0 o None: apagada, como en MT5
            return VELA1_PEQUENA
        if a.sin_noticias and self.noticias.get(hora.date()):
            return NOTICIAS
        if a.antes_de_noticias:
            primera = _primera_hora(self.noticias.get(hora.date(), []))
            if primera is not None and hora.time() <= primera:
                return ANTES_DE_NOTICIAS  # «el precio no tiene por qué llegar a ningún sitio si va a llegar con la noticia»
        if a.exigir_3h and not _acompana(colores["h3"], a.exigir_3h):
            return H3_NO_ACOMPANA
        if a.exigir_1h and not _acompana(colores["h1"], a.exigir_1h):
            return H1_NO_ACOMPANA
        if a.sin_banderas and banderas:
            return CON_BANDERAS
        if a.max_banderas is not None and len(banderas) > a.max_banderas:
            return CON_BANDERAS
        if a.vetar_tomando and any(b in banderas for b in (*B_DIARIO_TOMANDO.values(), *B_4H_TOMANDO.values())):
            return CON_BANDERAS  # «nunca estar vendiendo tras tomar bajos»
        if a.apertura_del_dia and any(b in banderas for b in B_APERTURA_DEL_DIA.values()):
            return AL_OTRO_LADO
        if self.pausa_hasta is not None and dia <= self.pausa_hasta:
            return PAUSA
        if a.perdida_max_dia_r and self.r_por_dia.get(dia, 0.0) <= -a.perdida_max_dia_r:  # 0 o None: sin tope, como en MT5
            return TOPE_DE_PERDIDA
        if self.por_dia[dia] >= a.max_operaciones_dia:
            return TOPE_DEL_DIA
        return None

    def _senal(self, hora, d, decision, color_diario, diario, setup, objetivo, op, colores, banderas) -> Senal:
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
            colores["h3"],
            colores["h1"],
            banderas,
        )

    # ───────────────────────── Fotos, cierres y salidas ─────────────────────────

    def _foto(self, hora: datetime, precio: float) -> None:
        self.res.fotos.append(
            Foto(
                hora,
                self._sesgo(),
                {d: self.d1.color(d, precio) for d in (+1, -1)},
                {d: self.h4.color(d, precio) for d in (+1, -1)},
                {d: self.h1.color(d, precio) for d in (+1, -1)},
            )
        )

    def _cerrar(self, m: Marco, hora: datetime, cierre: float) -> None:
        """Cierra la vela en curso de un marco. Con la regla candidata de salida por 1H, si al cerrar la
        vela de 1H se forma un rango en contra de una operación, la cierra o le lleva el stop a la entrada
        («cuando veo esto, tengo que poner break even y no comerme el stop», vídeo de los stops)."""
        nuevo = m.cerrar()
        if m is not self.h1 or not self.ajustes.salida_1h or nuevo is None or nuevo.tipo != "rango":
            return
        if self.abierta is not None and nuevo.direccion == -self.abierta.direccion and self._salida_1h(self.abierta, hora, cierre):
            self._cerrada(self.abierta)
        self.fantasmas = [op for op in self.fantasmas if not (nuevo.direccion == -op.direccion and self._salida_1h(op, hora, cierre))]

    def _sale(self, op: Operacion, barra: Vela, anterior: Vela | None) -> bool:
        """¿Se cierra la operación en esta barra? Stop o TP y las salidas candidatas. Si sigue abierta y toca,
        se lleva el stop a la entrada antes de la vela de las 9."""
        if _revisar_salida(op, barra, self.mercado, self.ajustes) or self._peligro(op, barra, anterior) or self._por_tiempo(op, barra):
            return True
        self._be_antes_de_las_9(op, barra)
        return False

    def _por_tiempo(self, op: Operacion, barra: Vela) -> bool:
        """Regla candidata de la salida por tiempo (vídeo de las salidas): ganando, si una vela de 4H que abrió
        después de la entrada supera el extremo de la anterior a favor (en compras, un máximo nuevo), se sale al
        cierre de esa barra, porque puede formar un rango al revés. Devuelve True si la operación se cierra."""
        d, vela = op.direccion, self.h4.parcial
        if not self.ajustes.salida_por_tiempo or vela is None or vela.inicio < op.hora_entrada or not self.h4.tomando(d):
            return False
        precio = _precio_de_salida(op, barra.cierre, self.mercado)
        if (precio - op.entrada) * d <= 0:
            return False
        _salir(op, barra.inicio + QUINCE_MIN, precio, SALIDA_POR_TIEMPO)
        return True

    def _be_antes_de_las_9(self, op: Operacion, barra: Vela) -> None:
        """Regla candidata (vídeo del backtest): ganando, stop a la entrada al cierre de la barra de las 8:45,
        porque «es muy probable que la vela de las 9 vaya a hacer el nuevo alto»."""
        if not self.ajustes.be_antes_de_las_9 or op.stop_en_entrada or (barra.inicio + QUINCE_MIN).time() != VELA_DE_LAS_9:
            return
        if (_precio_de_salida(op, barra.cierre, self.mercado) - op.entrada) * op.direccion > 0:
            op.stop, op.stop_en_entrada = op.entrada, True  # vale desde la barra siguiente

    def _peligro(self, op: Operacion, barra: Vela, anterior: Vela | None) -> bool:
        """Regla candidata de la «zona de peligro» (vídeo de los 6.000 $): ganando, si la vela de 4H y la de
        1H en curso hacen máximos nuevos (en ventas, mínimos) y una vela de M15 barre la anterior y vuelve a
        cerrar dentro, se sale al cierre de esa vela: «la probabilidad de que el precio se gire tras hacer
        nuevos altos va aumentando». Devuelve True si la operación se cierra."""
        d = op.direccion
        if not self.ajustes.salida_peligro or anterior is None or not (self.h4.tomando(d) and self.h1.tomando(d)):
            return False
        precio = _precio_de_salida(op, barra.cierre, self.mercado)
        m15 = evaluar(anterior, barra, "M15")
        if (precio - op.entrada) * d <= 0 or m15 is None or m15.tipo != "rango" or m15.direccion != -d:
            return False
        _salir(op, barra.inicio + QUINCE_MIN, precio, ZONA_DE_PELIGRO)
        return True

    def _salida_1h(self, op: Operacion, hora: datetime, cierre: float) -> bool:
        """Devuelve True si la operación se cierra."""
        precio = _precio_de_salida(op, cierre, self.mercado)
        if self.ajustes.salida_1h == "entrada" and (precio - op.entrada) * op.direccion > 0:
            op.stop, op.stop_en_entrada = op.entrada, True  # vale desde la barra siguiente
            return False
        _salir(op, hora, precio, SALIDA_1H)
        return True

    def _cerrada(self, op: Operacion) -> None:
        """La operación real se ha cerrado: se guarda y se lleva la cuenta del día y de la racha de stops."""
        self.res.operaciones.append(op)
        self.abierta = None
        dia = dia_de_trading(op.hora_salida - QUINCE_MIN)
        self.r_por_dia[dia] += op.r
        self.racha = self.racha + 1 if op.r < 0 else 0
        n = self.ajustes.pausa_tras_stops
        if n and self.racha >= n:
            self.pausa_hasta, self.racha = _siguiente_dia_habil(dia), 0

    def _cerrar_todo(self, hora: datetime, cierre: float, resultado: str = CIERRE_SEMANAL) -> None:
        """Cierra lo abierto (la real y las fantasma) al precio de cierre: fin de semana, hueco o fin del día."""
        for op in [self.abierta, *self.fantasmas]:
            if op is not None:
                _salir(op, hora, _precio_de_salida(op, cierre, self.mercado), resultado)
        if self.abierta is not None:
            self._cerrada(self.abierta)
        self.fantasmas = []


def _acompana(color: str, exigencia: str) -> bool:
    return color == "verde" if exigencia == "verde" else color != "rojo"


def _primera_hora(noticias: list) -> time | None:
    """La hora de la primera noticia del día («08:30 Nóminas…»), o None si ninguna la lleva."""
    horas = [time.fromisoformat(n[:5]) for n in noticias if len(n) >= 5 and n[2] == ":" and n[:2].isdigit() and n[3:5].isdigit()]
    return min(horas) if horas else None


def _siguiente_dia_habil(dia: date) -> date:
    siguiente = dia + timedelta(days=1)
    while siguiente.weekday() >= 5:
        siguiente += timedelta(days=1)
    return siguiente


def _niveles(d: int, precio: float, setup: Setup, mercado: Mercado, ratio: float, tp_objetivo: bool = False, tp_hasta_4h: bool = False):
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
    objetivo_4h = setup.objetivo if d > 0 else setup.objetivo + mercado.diferencial
    if not tp_objetivo:
        tp = entrada + d * ratio * riesgo
        if tp_hasta_4h and (objetivo_4h - tp) * d > 0:
            tp = objetivo_4h  # regla candidata: «al menos ratio 2… o el objetivo», si el del 4H está más lejos
        return entrada, stop, riesgo, tp
    # Regla candidata: el TP en el objetivo del rango de 4H («en fondeo solo voy a por los primeros objetivos»).
    if (objetivo_4h - entrada) * d < MINIMO_R_OBJETIVO * riesgo:
        return OBJETIVO_CERCA
    return entrada, stop, riesgo, objetivo_4h


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
