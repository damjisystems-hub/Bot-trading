# Bot CRT para MT5

`BotCRT.mq5` es el bot que funciona dentro de MetaTrader 5. Hace lo mismo que la prueba con el pasado en Python
(`crt/`), con las mismas reglas y en el mismo orden:

- Vigila el mercado del gráfico en diario, 4H, 3H, 1H y M15.
- Cuando sale una entrada, **os avisa al móvil**, con la nota de la situación y sus banderas rojas.
- **Apunta cada situación** en su memoria: las que toma y las que descarta, y por qué.
- **Os frena** (vídeo de psicología): con el tope de pérdida del día entre todos los mercados, deja de avisar y os
  dice que cerréis el gráfico.

**Estado (20-10-2026, versión 1.11):** está escrito, pero no se ha podido compilar en la sesión de Claude. Puede que al
compilarlo salga algún error. Si pasa, copiad el texto del error y pasádselo a Claude (ver la sección 8).

**Por defecto solo avisa.** Nunca opera en una cuenta real, salvo que lo activéis a propósito.

## 1. Instalarlo (una vez)

1. En MT5: **Archivo → Abrir carpeta de datos**.
2. Entrad en `MQL5` → `Experts` y copiad ahí `BotCRT.mq5`.
3. En MT5: **Herramientas → MetaQuotes Language Editor** (o la tecla F4).
4. En el panel de la izquierda de MetaEditor, abrid `Experts` → `BotCRT.mq5`.
5. Pulsad **Compilar** (o la tecla F7).
   - Abajo, en la pestaña «Errores», tiene que poner **0 errores**.
   - Los avisos («warnings») no importan.
6. Volved a MT5. En el panel «Navegador», en «Asesores expertos», aparece **BotCRT**. Si no aparece, botón derecho →
   «Actualizar».

## 2. Ponerlo en los tres mercados

1. Abrid un gráfico de cada mercado:
   - NASDAQ: según el bróker se llama NAS100, US100 o USTEC;
   - EURUSD;
   - XAUUSD (oro).
2. Poned los gráficos en M15. No es obligatorio, porque el bot usa siempre las barras de 15 minutos, pero así se ve lo
   mismo que él.
3. Arrastrad **BotCRT** a cada gráfico. En la ventana que se abre:
   - pestaña «Parámetros de entrada»: ajustad el **colchón del stop** de ese mercado (tabla de la sección 4);
   - pestaña «Común»: marcad «Permitir trading algorítmico» solo si vais a usar el modo demo.
4. Arriba a la izquierda del gráfico aparece el **panel** (sección 5).

MT5 tiene que estar abierto para que el bot funcione. Con el ordenador apagado no avisa. Su horario va de la 1:00 a las
13:00 de Nueva York, que suelen ser las 7:00 a 19:00 en España.

## 3. Avisos al móvil

1. Instalad la app **MetaTrader 5** en el móvil.
2. En la app: Ajustes → Mensajes. Ahí está vuestro **MetaQuotes ID**: copiadlo.
3. En el MT5 del ordenador: **Herramientas → Opciones → Notificaciones**.
4. Marcad «Activar notificaciones push», pegad el MetaQuotes ID y pulsad «Probar».

Un aviso es así:

> BOT CRT · COMPRA NAS100 · tras la apertura · Entrada 21480.5 · Stop 21410.0 · TP 21621.5 · 1 a 2 · 1 % = 0.35 lotes ·
> Escenario 3 · Nota B (el 1H va en contra) · Hoy: 14:00 FOMC Statement

- **Nota:** A, sin banderas rojas; B, con una; C, con dos o más. Las banderas son lo que el autor no quiere ver al entrar
  (ver `ESTRATEGIA.md`). No impiden entrar: sirven para que veáis el riesgo y para que el bot aprenda si importan.
- Cuando la operación termina, llega otro aviso con el resultado (TP, SL, salida por 1H, zona de peligro o cierre del
  viernes) en R.
- Si se llega al tope de pérdida del día, llega un aviso (solo uno, aunque el bot esté en los tres gráficos) y ese día ya
  no avisa de más entradas.

## 4. Parámetros

| Parámetro | Qué hace | Por defecto |
|---|---|---|
| **Qué hace el bot** | | |
| Modo | «Solo avisos» u «Operar en una cuenta demo». | Solo avisos |
| PermitirCuentaReal | Deja operar en una cuenta real. **No lo activéis** sin hablarlo antes. | No |
| RiesgoPct | Lo que se arriesga en cada operación, en % del balance. Sirve para calcular los lotes. | 1 |
| NombreMercado | El nombre que sale en los avisos y en la memoria. Vacío = el del símbolo. Para que coincida con el Python: NASDAQ, EUR/USD u Oro (XAU/USD). | vacío |
| **Reglas** | | |
| Ratio | El TP está a tantas veces lo que se arriesga. | 2 |
| EsperaAperturaMin | Minutos sin entrar después de la apertura de las 9:30 de Nueva York. | 45 |
| HoraDesde / HoraHasta | Horario de entradas, en hora de Nueva York. | 01:00 / 13:00 |
| SoloTrasApertura | Solo entradas después de la apertura. | No |
| SoloLondres | Solo entradas antes de la apertura. | No |
| MaxOperacionesDia | Máximo de operaciones al día en este mercado. | 2 |
| ColchonStopPuntos | Margen del stop detrás del barrido, en puntos del símbolo. Ver la tabla de abajo. | 30 |
| DiarioBastaNoRojo | Si está activado, basta con que el diario no vaya en contra. Lo decidido es que vaya a favor. | No |
| ComprobarObjetivoDiario | No entra si el TP queda más allá del objetivo del diario. | Sí |
| PerdidaMaxDiaR | Tope de pérdida del día, en R, **sumando todos los mercados** en los que esté puesto el bot (1 R = el 1 % con el riesgo por defecto). Al llegar, ese día ya no entra. 0 = sin tope. | 3 |
| HoraInicio4H | Hora de Nueva York a la que empiezan las velas de 4H: 17 en MT5 y forex (velas de la 1, las 5 y las 9); 18 en el gráfico de futuros de TradingView (velas de las 2, las 6 y las 10). | 17 |
| **Reglas candidatas** | Apagadas hasta que el laboratorio las pruebe y el equipo las apruebe. | |
| StopAEntradaEnR | Al llegar a +X R, el stop pasa a la entrada. 0 = no. | 0 |
| Vela1Minima | La vela 1 del rango de 4H tiene que ser al menos X veces el tamaño medio de las velas de 4H. 0 = no. | 0 |
| SinNoticias | No entra los días con noticias fuertes. | No |
| EscenariosPermitidos | Solo esos escenarios, por ejemplo `1,2`. Vacío = todos. | vacío |
| Salida1H | Si se forma un rango de 1H en contra: «Salir», o «Stop a la entrada si va ganando; si no, salir». | No |
| TpEnObjetivo4H | El TP va al objetivo del rango de 4H y no a 1 a Ratio. Si queda a menos de 1 R, no entra. | No |
| Exigir1H / Exigir3H | Que el 1H (o el 3H) esté a favor, o que al menos no vaya en contra. | No |
| SoloSinBanderas | Solo situaciones con nota A. | No |
| PausaTrasStops | Tras tantos stops seguidos, el resto del día y el siguiente sin entrar. 0 = no. | 0 |
| ToleranciaDiario | Un rango diario que cierra un poco por fuera (hasta esa parte de la vela 1) sigue valiendo, como hace el autor en el gráfico de futuros. 0 = no. | 0 |
| DiarioValeExpansiva | Tras una vela diaria expansiva a favor (cierra por fuera de la anterior) también vale, con el objetivo en su máximo (en ventas, su mínimo). | No |
| SalidaPeligro | Sale en la «zona de peligro»: ganando, con máximos nuevos en 4H y en 1H (en ventas, mínimos) y una vela de M15 que barre la anterior y cierra dentro. | No |
| **Datos y memoria** | | |
| DesfaseServidorNY | Horas que el reloj del servidor va por delante de Nueva York (ver abajo). | 7 |
| DiferencialFijoPuntos | 0 = usa el diferencial real del bróker. Con un número, usa siempre ese (sirve para comparar con el Python). | 0 |
| MesesHistoria | Meses de historia que repasa al arrancar, para saber cómo está el mercado. | 24 |
| EscribirMemoriaHistorica | Apunta también en la memoria lo que habría hecho en esa historia. | No |
| ExportarNoticias | Al arrancar, guarda las noticias fuertes de USD y EUR en `noticias.csv` para el laboratorio. | No |
| AniosNoticias | Años de noticias que exporta. | 3 |
| NumeroMagico | Número con el que el bot marca sus órdenes. | 20261020 |

**Colchón del stop.** Mirad cuántos decimales tiene el precio en vuestro bróker:

| Mercado | Precio de ejemplo | ColchonStopPuntos | Equivale a |
|---|---|---|---|
| NASDAQ con 1 decimal | 21480.5 | 30 | 3 puntos del índice |
| NASDAQ con 2 decimales | 21480.50 | 300 | 3 puntos del índice |
| EUR/USD | 1.08345 | 10 | 1 pip |
| Oro | 2650.25 | 50 | 0,50 $ |

**La hora del servidor.** Casi todos los brókeres van 7 horas por delante de Nueva York (GMT+2 en invierno, GMT+3 en
verano). Para comprobarlo: cuando en Nueva York son las 9:30, el reloj de «Observación de mercado» tiene que marcar las
16:30. Si marca otra hora, cambiad DesfaseServidorNY.

## 5. El panel

```
BOT CRT · NAS100 · solo avisa
Sesgo de fondo: COMPRAS   (semanal: compras · mensual: compras)
Diario:  compras verde · ventas rojo
4H:      compras ambar · ventas ambar
3H:      compras verde · ventas ambar
1H:      compras ambar · ventas rojo
Ahora:   se puede entrar (10:20 en Nueva York)
Hoy:     -1,0 R en este mercado · -2,0 R entre todos (tope: -3 R)
Racha:   1 stop seguido
Operación: ninguna
Fantasmas siguiéndose: 2
Última señal: 2026-10-20 10:30 · compra · entrada
```

- **Sesgo de fondo:** lo que el bot calcula con el semanal y el mensual. Es lo que tenéis que confirmar o cambiar cada
  lunes. Con «sin sesgo» no entra.
- **Diario y 4H:** el semáforo para compras y para ventas. Para entrar, los dos tienen que estar en verde hacia el lado
  del sesgo.
- **3H y 1H:** su color, para ver si acompañan. No hace falta que estén en verde (salvo con Exigir1H o Exigir3H), pero
  si van en contra es una bandera roja.
- **Ahora:** si en este momento puede entrar, si está esperando tras la apertura o si está fuera de horario.
- **Hoy:** lo que llevan hoy las operaciones del bot en este mercado y en todos. Cuando se llega al tope pone «TOPE
  ALCANZADO» y ya no entra hasta el día siguiente. Es el «bloqueador» que recomienda el vídeo de psicología.
- **Racha:** los stops seguidos. A partir de 3 os aconseja parar un día. Con PausaTrasStops, la pausa la hace él.
- **Operación:** la que tiene abierta. Si pone «de la historia, sin aviso», es una operación que habría tomado antes
  de arrancar: no se avisó, pero hasta que se cierre no toma otra, igual que la prueba en Python.
- **Fantasmas:** señales descartadas que sigue para saber qué habría pasado.
- **Última señal:** la última situación que ha visto y qué decidió.

## 6. La memoria

- Está en MT5 → Archivo → Abrir carpeta de datos → `MQL5` → `Files` → `BotCRT` → `memoria_<mercado>.csv`. Se abre con
  Excel o Numbers.
- Tiene una fila por situación, la tome o no:
  - qué decidió y por qué;
  - cómo estaban el sesgo, el diario y el 4H;
  - el escenario y si había noticias fuertes;
  - cómo estaban el 3H y el 1H, las banderas rojas y la nota (A, B o C);
  - y, cuando se cierra, el resultado, hasta dónde llegó a favor y hasta dónde llegó en contra.
- Tiene las mismas columnas que la memoria del Python, así que el mismo informe sirve para las dos.
- **Para que Claude aprenda de ella:** pasadle el archivo (por ejemplo, copiándolo en la carpeta `datos/` del
  repositorio). Claude ejecuta `python3 aprender.py --memoria-mt5 datos/memoria_NAS100.csv` y os explica qué
  situaciones ganan, cuáles pierden y qué habría pasado con las descartadas.
- `noticias.csv` (con ExportarNoticias) va en la misma carpeta. Sirve para que el laboratorio pruebe la regla de no
  operar los días de noticias.

## 7. Seguridad

- Por defecto **solo avisa**.
- Solo opera si se cumplen las tres cosas:
  - Modo = «Operar en una cuenta demo»;
  - la cuenta es demo;
  - el «Trading algorítmico» de MT5 está activado.
- En una cuenta real no opera, salvo con PermitirCuentaReal. Si alguien lo activa, el bot lo grita en el diario de MT5
  al arrancar.
- Si MT5 se desconecta y una señal le llega con más de 20 minutos de retraso, no avisa ni opera, pero la apunta.
- El viernes a las 17:00 de Nueva York cierra lo que haya abierto.
- **Tope de pérdida del día:** cada bot deja lo que lleva hoy en una variable global de MT5 (Herramientas → Variables
  globales, las que empiezan por `BotCRT.`) y suma las de los demás. Así el tope vale para los tres mercados juntos.
  Cuenta las operaciones del bot, no las que hagáis a mano: esas, apuntadlas en el cuaderno (`cuaderno/`).
- En el probador de estrategias de MT5 no hay calendario de noticias ni avisos al móvil.

## 8. Si algo falla al compilar

Copiad el texto exacto del error (con su número de línea) y pasádselo a Claude. Las partes con más riesgo son:

- las funciones del calendario económico (`CalendarValueHistory`, `CalendarEventById`), que piden un MT5 actualizado;
- `input group`, que también pide un MT5 de los últimos años;
- el cálculo de lotes (`OrderCalcProfit`) y las órdenes (`CTrade`);
- las variables globales del tope de pérdida (`GlobalVariableSet`, `GlobalVariableSetOnCondition`).

## 9. Comprobar que decide igual que el Python

1. Exportad de MT5 las barras de M15 del mismo periodo (ver el `README.md` del repositorio).
2. Poned en el bot:
   - DiferencialFijoPuntos con el diferencial de `crt/mercados.py`: NASDAQ con 1 decimal, 15; EUR/USD, 8; oro, 30;
   - ColchonStopPuntos con el colchón de la tabla;
   - EscribirMemoriaHistorica activado.
3. Pasadle a Claude la memoria y las barras. Las dos memorias tienen que tener las mismas entradas, salvo en los
   primeros días, mientras el bot «se pone al día».
