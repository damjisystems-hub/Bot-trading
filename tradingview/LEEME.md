# Indicador CRT para TradingView

Las mismas reglas que el bot, pintadas en el gráfico de TradingView, para verlas y decidir vosotros. Lo comprueba una
prueba automática: con los mismos precios, el indicador hace las mismas entradas, con el mismo stop y el mismo
objetivo, y descarta las mismas señales por los mismos motivos que el bot (`tests/test_tradingview.py`).

**Lo honesto:** son las mismas reglas que en 20 años perdieron unos −0,10 R por operación (ver `ESTRATEGIA.md`). El
indicador no cambia eso. Sirve para ver lo que ve el bot, aprender a leer la estrategia y apuntar en el cuaderno lo que
hacéis vosotros. Si el autor gana, su ventaja está en lo que decide a ojo, y eso lo ponéis vosotros.

**Estado (22-11-2026):** escrito y comprobado aquí (la sintaxis y que decide igual que el bot), pero no se ha podido
abrir en TradingView desde la sesión de Claude. Si al añadirlo sale un error, haced una captura y pasádsela a Claude.

## Los dos archivos

| Archivo | Para qué |
|---|---|
| `CRT_indicador.pine` | El de cada día: dibuja las señales, el panel y los casos, y avisa. |
| `CRT_estrategia.pine` | El mismo, como estrategia: para la **prueba con el pasado** de TradingView (el «Probador de estrategias»). |

No se editan a mano: salen de `plantilla.pine` con `python3 tradingview/generar.py`.

## Ponerlo en TradingView (una vez)

1. Entrad en https://www.tradingview.com y abrid un gráfico (botón «Gráfico» arriba).
2. Elegid el mercado:

   | Mercado | Símbolo recomendado |
   |---|---|
   | Euro | `OANDA:EURUSD` |
   | Libra | `OANDA:GBPUSD` |
   | Oro | `OANDA:XAUUSD` |
   | NASDAQ | `OANDA:NAS100USD` |

   El indicador reconoce el mercado por el nombre (EURUSD, GBPUSD, XAU o GOLD, y NAS, US100, USTEC, NQ o NDX) y pone
   solo el diferencial y el colchón del bot.
3. Poned el gráfico en **15 minutos** (arriba, «15m»). Con otro marco no calcula nada y lo avisa.
4. Abajo del todo, abrid **«Pine Editor»**.
5. Borrad lo que haya, pegad todo el texto de `CRT_indicador.pine`, pulsad **Guardar** y después **«Añadir al gráfico»**.
6. Para la prueba con el pasado, haced lo mismo con `CRT_estrategia.pine` en otra pestaña del editor.

## Qué se ve

- **COMPRA / VENTA** con su nota (A sin banderas rojas, B con una, C con dos o más). Al pasar el ratón por encima:
  la hora, la sesión, el rango de 4H, el diario, el sesgo, las banderas rojas, la entrada, el stop y el TP.
- **Líneas** de la entrada (gris), el stop (rojo) y el TP (verde) hasta que termina, con el resultado en R.
- **▲ / ▼ grises:** las señales que el bot descartó. Al pasar el ratón, el motivo (por ejemplo, «sin sesgo a favor»).
- **El objetivo del rango de 4H y el del diario** de ahora, con líneas a trazos.
- **El panel** (arriba a la derecha), como el de MT5:
  - el sesgo de fondo y los semáforos (diario, 4H, 3H y 1H);
  - si es horario de entradas, lo de hoy y la racha de stops;
  - la operación abierta;
  - los resultados en este gráfico y los casos del examen.
- **Los casos del examen** (las situaciones de los vídeos con fecha) que caen en la historia cargada: una caja verde si
  el indicador hizo lo mismo que el autor y roja si no. Al pasar el ratón, lo que pasó en el vídeo.

## Ajustes (rueda dentada del indicador)

- **Reglas:** las decididas, como en el bot (1 a 2, 45 minutos tras la apertura, de 1:00 a 13:00 de Nueva York, 2 al
  día, tope de −3 R, velas de 4H de la 1, las 5 y las 9). **Sesgo de esta semana:** lo que confirmáis cada lunes; solo
  vale para la semana en curso.
- **Reglas candidatas:** apagadas, porque en 20 años no ganan. Están para verlas, no para encenderlas sin más.
- **Costes:** el diferencial y el colchón del bot para cada mercado. Si vuestro bróker cobra otra cosa, cambiadlos.

## Avisos

1. En TradingView, botón **«Alerta»** (el reloj de arriba).
2. Condición: **CRT** → **«Cualquier llamada a la función alert()»**.
3. Marcad «Notificación en la app» para que llegue al móvil con la app de TradingView.

El aviso trae lo mismo que el del bot: compra o venta, entrada, stop, TP y nota. Para que llegue a Telegram hace falta
un «webhook», que TradingView solo tiene en sus planes de pago.

## Probar con el pasado

1. Con `CRT_estrategia.pine` añadido al gráfico, abajo, pestaña **«Probador de estrategias»**.
2. Ahí está el resultado: beneficio, factor de beneficio (más de 1 gana), operaciones, aciertos y caídas. El riesgo por
   operación (1 %) se cambia en los ajustes.
3. Para verlo vela a vela: botón **«Repetición»** (Bar Replay) arriba, y avanzad con la flecha.

Límites:
- **TradingView solo carga unos meses de velas de 15 minutos** (según el plan: el gratuito, unas 5.000 barras, que son
  dos o tres meses). La prueba de 20 años es la del bot en Python (`ESTRATEGIA.md`).
- Los casos más antiguos que la historia cargada salen como «fuera de la historia cargada».
- Las velas semanales y mensuales salen de la historia larga de TradingView, así que el sesgo vale desde el primer día.
- Cuando en una misma vela se tocan el stop y el TP, el probador de TradingView decide a su manera; el panel cuenta
  stop, como el bot.

## Para quien toque el código

- Las reglas se cambian en `ESTRATEGIA.md`, en `crt/`, en MT5 y aquí (en `plantilla.pine` y en `espejo.py`), y después
  `python3 tradingview/generar.py`.
- `espejo.py` es el indicador traducido a Python: la prueba lo compara con el bot sobre precios inventados.
- `generar.py` mete los costes de `crt/mercados.py` y los casos con fecha de `casos/casos.csv`.
