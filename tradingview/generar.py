#!/usr/bin/env python3
"""Escribe los dos scripts de TradingView a partir de plantilla.pine:

- CRT_indicador.pine: el indicador (dibuja, avisa y lleva la cuenta en R);
- CRT_estrategia.pine: lo mismo como estrategia, para la prueba con el pasado de TradingView.

Mete los costes de cada mercado (crt/mercados.py) y los casos del examen con fecha (casos/casos.csv), para
que no se desfasen del bot. Uso: python3 tradingview/generar.py
"""

from __future__ import annotations

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

from crt.casos import leer_casos  # noqa: E402
from crt.mercados import MERCADOS  # noqa: E402

ARCHIVOS = {"indicador": "CRT_indicador.pine", "estrategia": "CRT_estrategia.pine"}
LARGO_TEXTO = 400  # los textos de los casos van en las etiquetas: cortos


def _cadena(texto: str) -> str:
    """Una cadena de Pine entre comillas dobles, sin saltos de línea."""
    limpio = " ".join(texto.split()).replace("\\", "/").replace('"', "'")
    if len(limpio) > LARGO_TEXTO:
        limpio = limpio[: LARGO_TEXTO - 1] + "…"
    return f'"{limpio}"'


def _numero(x: float) -> str:
    """Un número de Pine en forma decimal (0.00008, 3.0), sin notación científica."""
    texto = f"{x:.10f}".rstrip("0")
    return texto + "0" if texto.endswith(".") else texto


def mercados() -> str:
    def cadena_de(campo) -> str:
        partes = [f'mercado == "{clave}" ? {campo(m)}' for clave, m in MERCADOS.items()]
        return " : ".join(partes)

    return "\n".join([
        "difBot = " + cadena_de(lambda m: _numero(m.diferencial)) + " : 0.0",
        "colBot = " + cadena_de(lambda m: _numero(m.colchon)) + " : 0.0",
        "nombreMercado = " + cadena_de(lambda m: f'"{m.nombre}"') + " : syminfo.ticker",
    ])  # fmt: skip


def _hora(t) -> str:
    return f'timestamp(NY, {t.year}, {t.month}, {t.day}, {t.hour}, {t.minute})'


def casos(ruta: str) -> str:
    lista = [c for c in leer_casos(ruta) if c.desde is not None and c.hasta is not None and c.mercado in MERCADOS]
    filas = {
        "casoId": [_cadena(c.id) for c in lista],
        "casoMercado": [_cadena(c.mercado) for c in lista],
        "casoDesde": [_hora(c.desde) for c in lista],
        "casoHasta": [_hora(c.hasta) for c in lista],
        "casoEsperado": [_cadena(c.esperado) for c in lista],
        "casoTexto": [_cadena(f"{c.fuente}: {c.nota}") for c in lista],
    }
    return "\n".join(f"var {nombre} = array.from({', '.join(valores)})" for nombre, valores in filas.items())


def construir(tipo: str, plantilla: str | None = None, ruta_casos: str | None = None) -> str:
    """El script de un tipo («indicador» o «estrategia»), como texto."""
    if plantilla is None:
        with open(os.path.join(AQUI, "plantilla.pine"), encoding="utf-8") as f:
            plantilla = f.read()
    ruta_casos = ruta_casos or os.path.join(RAIZ, "casos", "casos.csv")
    otro = "ESTRATEGIA" if tipo == "indicador" else "INDICADOR"
    salida, dentro = [], None
    for linea in plantilla.splitlines():
        marca = linea.strip()
        if marca in ("//@INDICADOR", "//@ESTRATEGIA"):
            dentro = marca[3:]
            continue
        if marca == "//@FIN":
            dentro = None
            continue
        if dentro == otro:
            continue
        if marca == "//@CABECERA":
            salida.append(f"// Generado por tradingview/generar.py a partir de tradingview/plantilla.pine: no lo editéis a mano.")
            continue
        if marca == "//@MERCADOS":
            salida.append(mercados())
            continue
        if marca == "//@CASOS":
            salida.append(casos(ruta_casos))
            continue
        salida.append(linea)
    return "\n".join(salida) + "\n"


def main() -> int:
    for tipo, nombre in ARCHIVOS.items():
        texto = construir(tipo)
        with open(os.path.join(AQUI, nombre), "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"{nombre}: {len(texto.splitlines())} líneas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
