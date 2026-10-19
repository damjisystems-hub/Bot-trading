"""Rangos CRT: qué pasa entre dos velas seguidas del mismo marco.

- Rango alcista: la vela 2 toma el mínimo de la vela 1 y vuelve a cerrar dentro. Su objetivo es el
  máximo de la vela 1. El mínimo de la vela 2 es el barrido (el «turtle soup»): ahí va el stop.
- Rango bajista: lo mismo al revés.
- Ruptura: la vela 2 cierra por fuera de la vela 1. No es un rango: se espera que el precio siga.
- Si la vela 2 no toma ningún extremo, o toma los dos y cierra dentro, no pasa nada.

Un rango se completa cuando el precio toca su objetivo. Se anula cuando una vela de su marco cierra
con el cuerpo más allá del barrido; una mecha no lo anula.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count

_ids = count(1)


@dataclass
class Evento:
    marco: str
    tipo: str  # "rango" o "ruptura"
    direccion: int  # +1 alcista, -1 bajista
    i_formado: int  # barra de M15 con la que cerró la vela 2
    i_vela_inicio: int  # primera barra de M15 de la vela 2
    objetivo: float | None = None
    barrido: float | None = None
    escenario: str = "otro"  # por qué camino llegó (escenarios del primer vídeo)
    estado: str = "activo"  # activo, completado o anulado
    velas_desde: int = 0  # velas del marco cerradas desde que se formó
    velas_hasta_completar: int | None = None
    id: int = field(default_factory=lambda: next(_ids))

    def actualizar_con_barra(self, barra) -> None:
        """¿Ha tocado el precio el objetivo en esta barra?"""
        if self.tipo != "rango" or self.estado != "activo":
            return
        if (self.direccion > 0 and barra.maximo >= self.objetivo) or (
            self.direccion < 0 and barra.minimo <= self.objetivo
        ):
            self.estado = "completado"
            self.velas_hasta_completar = self.velas_desde + 1

    def actualizar_con_cierre(self, vela) -> None:
        """Al cerrar una vela del marco: ¿ha cerrado con el cuerpo más allá del barrido?"""
        if self.tipo != "rango" or self.estado != "activo":
            return
        self.velas_desde += 1
        if (self.direccion > 0 and vela.cierre < self.barrido) or (
            self.direccion < 0 and vela.cierre > self.barrido
        ):
            self.estado = "anulado"


def evaluar(v1, v2, marco: str) -> Evento | None:
    """El evento que forma la vela 2 respecto a la vela 1, o None si no forma ninguno."""
    if v2.cierre > v1.maximo:
        return Evento(marco, "ruptura", +1, v2.i_fin, v2.i_inicio)
    if v2.cierre < v1.minimo:
        return Evento(marco, "ruptura", -1, v2.i_fin, v2.i_inicio)
    toma_minimo = v2.minimo < v1.minimo
    toma_maximo = v2.maximo > v1.maximo
    if toma_minimo and not toma_maximo:
        return Evento(marco, "rango", +1, v2.i_fin, v2.i_inicio, objetivo=v1.maximo, barrido=v2.minimo)
    if toma_maximo and not toma_minimo:
        return Evento(marco, "rango", -1, v2.i_fin, v2.i_inicio, objetivo=v1.minimo, barrido=v2.maximo)
    return None


def semaforo(ultimo: Evento | None, direccion: int) -> str:
    """Color del semáforo de un marco para operar en una dirección, mirando solo velas cerradas.

    Verde: el último evento es un rango a favor que sigue activo. Rojo: es un rango en contra que
    sigue activo, o una ruptura en contra. Ámbar: todo lo demás (rango completado o anulado,
    ruptura a favor, o nada todavía).
    """
    if ultimo is None:
        return "ambar"
    if ultimo.tipo == "ruptura":
        return "rojo" if ultimo.direccion != direccion else "ambar"
    if ultimo.estado != "activo":
        return "ambar"
    return "verde" if ultimo.direccion == direccion else "rojo"


def escenario(previo: Evento | None, direccion: int) -> str:
    """Por qué camino del primer vídeo se llega a un rango a favor, según el evento que había antes:

    1: el rango en contra se completó en varias velas; 2: se completó en una sola vela;
    3: el rango a favor aparece antes de que se complete el que iba en contra; otro: lo demás.
    """
    if previo is None or previo.tipo != "rango" or previo.direccion == direccion:
        return "otro"
    if previo.estado == "activo":
        return "3"
    if previo.estado == "completado":
        return "2" if previo.velas_hasta_completar == 1 else "1"
    return "otro"
