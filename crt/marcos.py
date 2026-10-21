"""Un marco de tiempo (1H, 4H, diario…) tal como lo ve el bot: sus velas, sus rangos y su semáforo.

El semáforo puede ponerse en verde antes de que cierre la vela grande: si la vela en curso ya ha
barrido el extremo de la anterior (sin haber tomado también el otro, porque entonces ya no puede ser
un rango), el precio ha vuelto dentro y el marco menor ha formado un rango a favor después del
barrido. Es lo que hace el autor al bajar de 4H a 1H «para no esperar a que cierre la vela de 4H», y
de diario a 4H.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rangos import Evento, escenario, evaluar, semaforo
from .velas import QUINCE_MIN, Vela, clave_y_fin

MAX_VELAS_EVENTO = 60  # un rango que lleva tantas velas sin completarse deja de seguirse
VELAS_PARA_LA_MEDIA = 20  # el tamaño «normal» de una vela es la media de las últimas 20


@dataclass
class Setup:
    """Un rango a favor desde el que se puede buscar la entrada: cerrado o anticipado."""

    ids: tuple  # identifican la idea; la misma idea no da dos entradas
    direccion: int
    barrido: float  # el stop va detrás
    objetivo: float
    i_inicio: int  # la entrada tiene que llegar después de esta barra de M15
    via: str  # "cierre" (vela cerrada) o "anticipo" (con el marco menor)
    escenario: str
    vela1_rel: float | None = None  # tamaño de la vela 1 comparado con el tamaño medio de las velas del marco


class Marco:
    def __init__(self, nombre: str, menor: Marco | None = None, inicio_4h: int = 17, tolerancia: float = 0.0):
        self.nombre = nombre
        self.menor = menor
        self.inicio_4h = inicio_4h  # hora de Nueva York a la que empiezan las velas de 4H
        self.tolerancia = tolerancia  # cierre un poco por fuera que aún cuenta como rango (ver rangos.evaluar)
        self.cerradas: list[Vela] = []  # solo se guardan las últimas
        self.parcial: Vela | None = None  # la vela en curso
        self.clave = None
        self.fin = None
        self.eventos: list[Evento] = []  # rangos activos
        self.ultimo: Evento | None = None  # el último evento, que es el que manda en el semáforo
        self.i_barrido = {+1: None, -1: None}  # barra en la que la vela en curso barrió el mínimo (+1) o el máximo (-1) de la anterior

    # ───────────────────────── Velas ─────────────────────────

    def toca_cerrar_antes(self, barra: Vela) -> bool:
        """La barra pertenece a otra vela: hay que cerrar la que está en curso antes de sumarla."""
        return self.parcial is not None and clave_y_fin(self.nombre, barra.inicio, self.inicio_4h)[0] != self.clave

    def toca_cerrar_despues(self, barra: Vela) -> bool:
        """Con esta barra termina la vela en curso."""
        return self.parcial is not None and barra.inicio + QUINCE_MIN >= self.fin

    def actualizar_con_barra(self, barra: Vela) -> None:
        for e in self.eventos:
            if e.i_formado < barra.i_fin:
                e.actualizar_con_barra(barra)
        self.eventos = [e for e in self.eventos if e.estado == "activo"]

    def sumar(self, barra: Vela) -> None:
        if self.parcial is None:
            self.clave, self.fin = clave_y_fin(self.nombre, barra.inicio, self.inicio_4h)
            self.parcial = Vela(barra.inicio, barra.apertura, barra.maximo, barra.minimo, barra.cierre, barra.i_inicio, barra.i_fin)
            self.i_barrido = {+1: None, -1: None}
        else:
            self.parcial.sumar(barra)
        if self.cerradas:
            previa = self.cerradas[-1]
            if self.i_barrido[+1] is None and self.parcial.minimo < previa.minimo:
                self.i_barrido[+1] = barra.i_fin
            if self.i_barrido[-1] is None and self.parcial.maximo > previa.maximo:
                self.i_barrido[-1] = barra.i_fin

    def cerrar(self) -> Evento | None:
        vela, self.parcial = self.parcial, None
        for e in self.eventos:
            e.actualizar_con_cierre(vela)
        self.eventos = [
            e for e in self.eventos if e.estado == "activo" and (e.velas_desde < MAX_VELAS_EVENTO or e is self.ultimo)
        ]
        nuevo = evaluar(self.cerradas[-1], vela, self.nombre, self.tolerancia) if self.cerradas else None
        if nuevo is not None:
            nuevo.vela1_rel = self._relativo(self.cerradas[-1])
        self.cerradas.append(vela)
        del self.cerradas[: -(VELAS_PARA_LA_MEDIA + 1)]
        if nuevo is not None:
            nuevo.escenario = escenario(self.ultimo, nuevo.direccion)
            if nuevo.tipo == "rango":
                self.eventos.append(nuevo)
            self.ultimo = nuevo
        return nuevo

    def rango_medio(self) -> float | None:
        """Tamaño medio (máximo − mínimo) de las últimas velas cerradas, o None si aún hay pocas."""
        ultimas = self.cerradas[-VELAS_PARA_LA_MEDIA:]
        if len(ultimas) < 5:
            return None
        return sum(v.maximo - v.minimo for v in ultimas) / len(ultimas)

    def _relativo(self, vela: Vela) -> float | None:
        medio = self.rango_medio()
        return (vela.maximo - vela.minimo) / medio if medio else None

    # ───────────────────────── Semáforo ─────────────────────────

    def setup(self, direccion: int, precio: float) -> Setup | None:
        """El rango a favor desde el que buscar la entrada ahora mismo, o None si no lo hay."""
        e = self.ultimo
        if e is not None and e.tipo == "rango" and e.estado == "activo" and e.direccion == direccion:
            ids = (e.id, ("anticipo", self.nombre, e.i_vela_inicio, direccion))
            return Setup(ids, direccion, e.barrido, e.objetivo, e.i_formado, "cierre", e.escenario, e.vela1_rel)
        return self.anticipo(direccion, precio)

    def anticipo(self, direccion: int, precio: float) -> Setup | None:
        """El rango a favor que está formando la vela en curso, visto con el marco menor, o None."""
        if self.menor is None or self.parcial is None or not self.cerradas:
            return None
        i_barrido = self.i_barrido[direccion]
        previa = self.cerradas[-1]
        if i_barrido is None or not previa.minimo < precio < previa.maximo or self.tomando(direccion):
            return None
        menor = self.menor.setup(direccion, precio)
        if menor is not None and menor.via == "cierre" and menor.i_inicio < i_barrido:
            # El rango cerrado del marco menor es de antes del barrido: vale el que se esté formando ahora
            # (si no, un rango viejo de 4H que sigue activo taparía el verde anticipado del diario).
            menor = self.menor.anticipo(direccion, precio)
        if menor is None or menor.i_inicio < i_barrido:
            return None
        if direccion > 0:
            barrido, objetivo = self.parcial.minimo, previa.maximo
        else:
            barrido, objetivo = self.parcial.maximo, previa.minimo
        ids = (("anticipo", self.nombre, self.parcial.i_inicio, direccion),)
        return Setup(
            ids, direccion, barrido, objetivo, menor.i_inicio, "anticipo", escenario(self.ultimo, direccion), self._relativo(previa)
        )

    def color(self, direccion: int, precio: float) -> str:
        if self.setup(direccion, precio) is not None:
            return "verde"
        return semaforo(self.ultimo, direccion)

    def tomando(self, direccion: int) -> bool:
        """¿La vela en curso ya ha pasado el extremo de la anterior hacia ese lado? En compras, que está
        «tomando máximos»: si vuelve a cerrar dentro, forma un rango en contra (vídeo de los stops)."""
        if self.parcial is None or not self.cerradas:
            return False
        previa = self.cerradas[-1]
        return self.parcial.maximo > previa.maximo if direccion > 0 else self.parcial.minimo < previa.minimo
