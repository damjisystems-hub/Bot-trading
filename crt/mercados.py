"""Lo que cambia de un mercado a otro: lo que cuesta entrar (el diferencial) y el colchón del stop.

Son valores típicos de una cuenta CFD, no medidos en vuestro bróker. Si el vuestro cobra más, la
prueba con el pasado sale mejor de lo que saldrá en real: cambiadlos cuando sepáis los vuestros.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Mercado:
    nombre: str
    diferencial: float  # spread: diferencia entre el precio de compra y el de venta
    colchon: float  # margen del stop más allá del barrido
    decimales: int


MERCADOS = {
    "nasdaq": Mercado("NASDAQ", diferencial=1.5, colchon=3.0, decimales=1),
    "eurusd": Mercado("EUR/USD", diferencial=0.00008, colchon=0.0001, decimales=5),
    "oro": Mercado("Oro (XAU/USD)", diferencial=0.3, colchon=0.5, decimales=2),
}
