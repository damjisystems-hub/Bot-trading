# Bot CRT

Bot de trading con la estrategia CRT («Candle Range Theory») para el NASDAQ, el EUR/USD, la libra (GBP/USD) y el oro. Tiene cuatro partes:

- **El cerebro** (`crt/`): las reglas de la estrategia, en Python, con las banderas rojas de los vídeos.
- **El aprendizaje**:
  - la memoria de cada situación;
  - el laboratorio, que prueba reglas nuevas;
  - el examen con situaciones reales.
- **El bot en vivo para MT5** (`mt5/`): avisa al móvil, os frena con el tope de pérdida del día y, más adelante, opera
  en demo.
- **El cuaderno del equipo** (`cuaderno/`): vuestras operaciones y cómo estabais, para la parte de psicología.

**Estado (21-10-2026):**
- Las reglas, la memoria, el laboratorio, el examen y el cuaderno están programados y comprobados con pruebas
  automáticas. Ya tienen lo de los veintitrés vídeos: 13 banderas rojas, 38 reglas candidatas, 60 situaciones en el
  examen y la disciplina de los vídeos de psicología y de cuentas.
- **Prueba con datos reales del pasado (21 y 22-10-2026):** de 2005 a mayo de 2020 con precios de OANDA, y de 2021 a
  2025 con los de la demo de MetaQuotes (ver «Datos»). Con las reglas de hoy **pierde** en los tres tramos (unas 1.065
  operaciones y unos −106 R), y un rango de 4H solo se comporta como el azar. Ninguna idea de los vídeos lo arregla y el
  examen con los vídeos sale 8 de 32. Los detalles están en `ESTRATEGIA.md`, «Prueba con datos reales». No se usa con
  dinero real mientras pierda.
- El bot de MT5 compila y funciona en la demo de MetaQuotes desde el 22-10-2026, con avisos por Telegram (ver
  `mt5/LEEME.md`).
- **Autoaprendizaje (21-10-2026):** el bot aprende solo de sus peores situaciones y se corrige, con frenos para no
  aprender la suerte. En el Mac: doble clic en `Autoaprender.command` (ver `ESTRATEGIA.md`, «Autoaprendizaje»).
- **Para empezar en demo:** `mt5/LEEME.md`, sección 0 (paso a paso y la rutina de cada semana).
- No opera con dinero real.

- Las reglas exactas: [ESTRATEGIA.md](ESTRATEGIA.md).
- El flujo dibujado: https://claude.ai/artifact/MW8eiwC99U2ekSHkywnrfz (página privada).

## Cómo aprende

No cambia sus reglas solo: aprende con un método y vosotros aprobáis cada cambio.

1. **Memoria.** Apunta cada situación que ve, la tome o no, y por qué, con sus banderas rojas (lo que el autor no
   quiere ver al entrar) y una nota: A, B o C. Las señales que descarta las sigue como operaciones «fantasma» para
   saber qué habría pasado. Hace lo mismo el bot de MT5 en directo.
2. **Laboratorio.** Prueba cada regla candidata (las cosas que el autor hace a ojo, o lo que se os ocurra) en dos
   periodos. Solo la propone si mejora en los dos y con suficientes operaciones.
3. **Examen.** Situaciones reales que le enseñáis, de los vídeos o de lo que os pase, con lo que tenía que hacer
   (`casos/casos.csv`). Se examina con todas y explica qué hizo y por qué.
4. **Psicología.** El informe de la memoria cuenta las pérdidas «buenas», las rachas normales y si una operación
   influye en la siguiente. El cuaderno hace lo mismo con vuestras operaciones: proceso, emociones y reglas rotas.

**Para enseñarle una situación nueva**, decídsela a Claude: mercado, día, hora y qué tenía que hacer. Se añade al
examen. Si el bot falla, se busca por qué; si hace falta una regla, se prueba en el laboratorio y decidís vosotros.

## Órdenes

Solo hace falta Python 3.9 o más nuevo, sin instalar nada:

```
python3 probar.py datos/NAS100_M1.csv --mercado nasdaq
python3 aprender.py datos/NAS100_M1.csv --mercado nasdaq --noticias datos/noticias.csv
python3 examen.py datos/NAS100_M1.csv --mercado nasdaq
python3 aprender.py datos/EURUSD_2012_2020.csv --mercado eurusd --confirmar datos/EURUSD_2005_2011.csv
python3 diagnostico.py datos/EURUSD_M1.csv --mercado eurusd
python3 autoaprender.py --carpeta "<carpeta de datos de MT5>/MQL5/Files/BotCRT"
python3 cartera.py datos/EURUSD_M1.csv:eurusd datos/GBPUSD_M1.csv:gbpusd datos/NAS100_M1.csv:nasdaq datos/XAUUSD_M1.csv:oro
python3 aprender.py --memoria-mt5 datos/memoria_NAS100.csv
python3 cuaderno.py
```

- `probar.py`: la prueba con el pasado.
  - Saca cuántas operaciones salen, el acierto, el resultado en R (1 R es lo que se arriesga en cada operación), la
    peor racha y la peor caída.
  - Lo separa por sesión, escenario, dirección y año.
  - Con `--memoria` guarda la memoria y con `--comparar` compara las reglas candidatas.
- `aprender.py`: la prueba más la memoria (qué situaciones ganan y cuáles pierden, y qué habría pasado con las
  descartadas) más el laboratorio. Guarda la memoria en `resultados/`.
- `examen.py`: el examen con `casos/casos.csv`. Los datos tienen que empezar unos meses antes de los casos. Con
  `--modelo-del-backtest` se examina con el modelo del backtest del autor (sin sesgo ni diario), que es el de los casos
  «vbacktest-…».
- `aprender.py --confirmar`: las ideas que mejoran claramente se prueban también en otros datos que no se han usado
  para buscarlas (por ejemplo, otros años). Lo que no se confirma puede ser casualidad.
- `autoaprender.py`: el autoaprendizaje. Con `--carpeta`, lee los precios que exporta el bot de MT5 y le deja
  `reglas_aprendidas.txt`, que el bot lee solo cada día. En el Mac, `Autoaprender.command` hace lo mismo con doble clic.
- `diagnostico.py`: mira si un rango CRT, por sí solo (sin sesgo, diario ni order block), llega al objetivo más veces
  de lo que daría el azar.
- `cartera.py`: los mercados a la vez, como el bot de MT5 puesto en todos los gráficos. El tope de pérdida del día suma
  lo de todos. Saca la peor caída de la cuenta, el peor día y las veces que el euro y la libra van a la vez.
- `aprender.py --memoria-mt5`: el informe de lo que ha apuntado el bot de MT5 en directo.
- `cuaderno.py`: el informe de vuestro cuaderno de operaciones (`cuaderno/LEEME.md` explica cómo apuntarlas).
- Mercados: `nasdaq`, `eurusd`, `gbpusd` y `oro`.
- Las cifras dependen de los datos y de los costes supuestos de cada mercado (`crt/mercados.py`).

## Datos

Hacen falta barras de 1 o de 15 minutos de varios años de cada mercado:

1. **Desde MT5:**
   - Ver → Símbolos (Ctrl+U) → pestaña «Barras».
   - Elegid el símbolo, «M1» o «M15» y las fechas → «Solicitar» → «Exportar barras».
   - Guardad el archivo en `datos/`.
   - El programa supone que la hora del servidor es la de Nueva York + 7 (GMT+2 en invierno y GMT+3 en verano, lo
     normal). Si vuestro bróker usa otra, se cambia con `--desfase-servidor`.
   - Ojo: muchos brókeres solo dan unos meses de barras de 1 minuto.
2. **Dukascopy:** da años de datos de 1 minuto gratis. Desde la sesión de Claude en la nube está bloqueado
   (`datafeed.dukascopy.com`); se puede permitir en los ajustes de red del entorno.
3. **OANDA, de 2005 a mayo de 2020 (lo que se ha usado en la primera prueba; 2005–2011, solo para confirmar):** precios de 1 minuto en UTC del
   repositorio público de GitHub `FutureSharks/financial-data` (`pyfinancialdata/data/currencies/oanda/`: EUR_USD,
   GBP_USD, NAS100_USD y XAU_USD). Se juntan en barras de 15 minutos y se leen con `--formato utc`. Son precios de OANDA,
   no los de vuestro bróker, y terminan en 2020: no sirven para los casos del examen, que son de 2025 y 2026.
4. **Demo de MetaQuotes, de septiembre de 2021 a hoy (la prueba de los años recientes y el examen):** los
   `barras_ny_*.csv` que exporta el bot de MT5 cada día (en `datos/metaquotes_demo/`). Ya van en hora de Nueva York: se
   leen con `--formato mt5 --desfase-servidor 0`.
5. **Noticias:** el bot de MT5 las exporta desde su calendario económico con el parámetro `ExportarNoticias`
   (`noticias.csv`).

Los datos y los resultados no se suben a git (`datos/` y `resultados/` están en `.gitignore`).

## Pruebas automáticas

```
python3 -m unittest
```

## Mapa

| Ruta | Qué hay |
|---|---|
| `ESTRATEGIA.md` | Las reglas exactas, lo decidido, lo provisional y cómo aprende. |
| `probar.py`, `aprender.py`, `examen.py`, `cartera.py`, `diagnostico.py`, `cuaderno.py` | Las órdenes. |
| `crt/diagnostico.py` | Si un rango CRT solo tiene ventaja frente al azar. |
| `crt/autoaprendizaje.py`, `autoaprender.py`, `Autoaprender.command` | El autoaprendizaje: las peores situaciones, los frenos y el archivo de reglas aprendidas. |
| `casos/casos.csv` | Las situaciones del examen: las de los vídeos y las que le enseñéis. |
| `cuaderno/` | Vuestro cuaderno de operaciones (`operaciones.csv`) y cómo rellenarlo. |
| `crt/velas.py` | Lee el CSV (MT5 o UTC) y monta las velas de 1H, 3H, 4H, diario, semanal y mensual en hora de Nueva York. |
| `crt/rangos.py` | Rangos, rupturas, cuándo se completan o se anulan, el semáforo y los escenarios. |
| `crt/marcos.py` | Cada marco con sus velas, su semáforo y el verde anticipado con el marco menor. |
| `crt/entrada.py` | El order block de M15 y el horario. |
| `crt/motor.py` | La prueba con el pasado: hace lo que haría el bot, barra a barra, y apunta la memoria con las banderas rojas. |
| `crt/memoria.py` | La memoria en CSV (las mismas columnas que la del bot de MT5). |
| `crt/aprendizaje.py` | Qué situaciones ganan y cuáles pierden, y lo que dicen los números de la psicología. |
| `crt/cuaderno.py` | El informe del cuaderno del equipo. |
| `crt/laboratorio.py` | Las reglas candidatas y su prueba en dos periodos. |
| `crt/casos.py` | El examen. |
| `crt/noticias.py` | Las noticias fuertes, para avisar y para probar la regla de no operar esos días. |
| `crt/mercados.py` | Diferencial y colchón del stop de cada mercado (valores típicos, no medidos). |
| `crt/informe.py` | El resumen de la prueba. |
| `mt5/` | El bot en vivo para MT5 y su guía. |
| `tests/` | Pruebas automáticas con precios inventados. |
