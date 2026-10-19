# Bot CRT

El cerebro de un bot de trading con la estrategia CRT («Candle Range Theory») para el NASDAQ, el EUR/USD y el oro, y
la **prueba con datos del pasado** para saber si las reglas ganan antes de arriesgar dinero.

**Estado (19-10-2026):**
- Las reglas están programadas y comprobadas con 41 pruebas automáticas.
- **Falta la prueba con datos reales del pasado**, porque faltan los datos (ver «Datos»).
- Todavía **no** avisa al móvil ni opera.

- Las reglas exactas: [ESTRATEGIA.md](ESTRATEGIA.md).
- El flujo dibujado: https://claude.ai/artifact/MW8eiwC99U2ekSHkywnrfz (página privada).

## Probarlo con datos del pasado

Solo hace falta Python 3.9 o más nuevo, sin instalar nada:

```
python3 probar.py datos/NAS100_M1.csv --mercado nasdaq
python3 probar.py datos/NAS100_M1.csv --mercado nasdaq --comparar
python3 probar.py datos/XAUUSD_M1.csv --mercado oro --operaciones resultados/oro.csv
```

- Mercados: `nasdaq`, `eurusd` y `oro`.
- El informe dice cuántas operaciones salen, el porcentaje de acierto, el resultado en R, la peor racha y la peor caída.
  También lo separa por sesión (Londres o tras la apertura), escenario, dirección y año.
  - 1 R es lo que se arriesga en cada operación.
  - Con objetivo 1 a 2, para no perder hay que acertar más del 33 %.
- `--comparar` prueba también las variantes que quedaron abiertas:
  - 1 a 1;
  - 0, 30 o 60 minutos de espera tras la apertura;
  - solo después de la apertura;
  - un diario menos exigente.
- `--operaciones` guarda cada operación en un CSV.

## Datos

Hacen falta barras de 1 o de 15 minutos de varios años de cada mercado:

1. **Desde MT5:**
   - Ver → Símbolos (Ctrl+U) → pestaña «Barras».
   - Elegid el símbolo (por ejemplo NAS100, EURUSD o XAUUSD), «M1» o «M15» y las fechas → «Solicitar» → «Exportar
     barras».
   - Guardad el archivo en `datos/`.
   - El programa supone que la hora del servidor es la de Nueva York + 7 (GMT+2 en invierno y GMT+3 en verano, lo
     normal). Si vuestro bróker usa otra, se cambia con `--desfase-servidor`.
   - Ojo: muchos brókeres solo dan unos meses de barras de 1 minuto.
2. **Dukascopy:** da años de datos de 1 minuto gratis, pero desde la sesión de Claude en la nube está bloqueado
   (`datafeed.dukascopy.com`). Se puede permitir en los ajustes de red del entorno.

Los datos y los resultados no se suben a git (`datos/` y `resultados/` están en `.gitignore`).

## Pruebas automáticas

```
python3 -m unittest
```

## Mapa

| Ruta | Qué hay |
|---|---|
| `ESTRATEGIA.md` | Las reglas exactas, lo decidido y lo provisional. |
| `probar.py` | La orden para lanzar la prueba con el pasado. |
| `crt/velas.py` | Lee el CSV (MT5 o UTC) y monta las velas de 1H, 4H, diario, semanal y mensual en hora de Nueva York. |
| `crt/rangos.py` | Rangos, rupturas, cuándo se completan o se anulan, el semáforo y los escenarios. |
| `crt/marcos.py` | Cada marco de tiempo con sus velas y su semáforo, y el verde anticipado con el marco menor. |
| `crt/entrada.py` | El order block de M15 y el horario de entradas. |
| `crt/motor.py` | La prueba con el pasado: recorre las barras una a una y hace lo que haría el bot, sin mirar el futuro. |
| `crt/informe.py` | El resumen en texto. |
| `crt/mercados.py` | Diferencial y colchón del stop de cada mercado (valores típicos, no medidos). |
| `tests/` | Pruebas automáticas con precios inventados. |
