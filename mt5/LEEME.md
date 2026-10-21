# Bot CRT para MT5

`BotCRT.mq5` es el bot que funciona dentro de MetaTrader 5. Hace lo mismo que la prueba con el pasado en Python
(`crt/`), con las mismas reglas y en el mismo orden:

- Vigila el mercado del gráfico en diario, 4H, 3H, 1H y M15.
- Cuando sale una entrada, **os avisa al móvil**, con la nota de la situación y sus banderas rojas.
- **Apunta cada situación** en su memoria: las que toma y las que descarta, y por qué.
- **Os frena** (vídeo de psicología): con el tope de pérdida del día entre todos los mercados, deja de avisar y os
  dice que cerréis el gráfico.

**Estado (21-10-2026, versión 1.16):** está escrito, pero no se ha podido compilar en la sesión de Claude. Puede que al
compilarlo salga algún error. Si pasa, copiad el texto del error y pasádselo a Claude (ver la sección 8).

**Por defecto solo avisa.** Nunca opera en una cuenta real, salvo que lo activéis a propósito.

## 0. Empezar en demo, paso a paso

Nada de dinero real. El bot no va a ser perfecto el primer día. Lo que sí se puede hacer es comprobarlo por partes antes
de fiarse de él. Por este orden:

1. **Una cuenta demo de MT5.**
   - Hace falta un bróker con MT5 y los cuatro mercados: NASDAQ (NAS100, US100 o USTEC), EURUSD, GBPUSD y XAUUSD. Por
     ejemplo Axi, que es el que usa el autor para su cuenta propia en el curso desde 0, aunque cualquiera con MT5 sirve.
   - Abridla con el dinero que pensáis poner después en la cuenta propia: así los lotes y las pérdidas se ven de verdad.
   - Comprobad la hora del servidor: cuando en Nueva York son las 9:30, el reloj de «Observación de mercado» tiene que
     marcar las 16:30. Si marca otra hora, cambiad DesfaseServidorNY (sección 4).
2. **MT5 en el ordenador.** Se descarga de la web oficial, metatrader5.com. Tiene versión para Mac (funciona dentro de
   Wine), con MetaEditor dentro. Entrad con la cuenta demo: en el título de la ventana tiene que poner «Demo», no
   «Live» ni «Real».
3. **Instalar y compilar el bot** (sección 1). Hasta que no compile con 0 errores, no funciona. Si sale algún error,
   copiad el texto y pasádselo a Claude: lo arregla y os da el archivo nuevo.
4. **Exportar la historia y pasársela a Claude** (`README.md`, «Datos»): barras de M1 o de M15 de los cuatro mercados,
   todos los meses que dé el bróker. Con eso Claude hace:
   - la primera prueba con datos reales del pasado (todavía no hay ninguna);
   - el examen con las situaciones de los vídeos;
   - la comparación con lo que decide el bot de MT5 (sección 9), para asegurar que los dos deciden igual.
5. **Verlo funcionar con el pasado (opcional).** En MT5: Ver → Probador de estrategias. Elegid BotCRT, el símbolo, M15,
   unas semanas de fechas y «Visualización». Se ve cómo marca entradas, stops y TP sobre el gráfico. En el probador no
   hay noticias ni avisos al móvil.
6. **Ponerlo en los cuatro gráficos** (sección 2). Cambiad solo esto; lo demás, como viene:

   | Parámetro | NASDAQ | EUR/USD | GBP/USD | Oro |
   |---|---|---|---|---|
   | Modo | Operar en una cuenta demo | igual | igual | igual |
   | NombreMercado | NASDAQ | EUR/USD | GBP/USD | Oro (XAU/USD) |
   | ColchonStopPuntos | 30 (precio con 1 decimal) o 300 (con 2) | 10 | 15 | 50 |
   | ExportarNoticias | Sí, la primera vez | No | No | No |

   - En la pestaña «Común», marcad «Permitir trading algorítmico». Arriba en MT5, el botón «Trading algorítmico» tiene
     que estar en verde.
   - El riesgo (1 %) y el tope del día (3 R) ya vienen puestos, como está decidido. PermitirCuentaReal, siempre «No».
   - Las reglas candidatas, apagadas: solo se encienden si el laboratorio las aprueba y lo decidís vosotros.
7. **Avisos al móvil** (sección 3).
8. **El ordenador, encendido toda la semana** (del domingo por la noche al viernes a las 23:00, hora de España), con
   MT5 abierto y sin que entre en reposo. Las entradas son de 7:00 a 19:00 de España, pero una operación puede seguir
   abierta de noche y el viernes el bot la cierra a las 16:45 de Nueva York (22:45 en España). Si el ordenador se
   apaga:
   - la operación sigue en la cuenta con su stop y su TP, pero sin el cierre del viernes ni las salidas por reglas;
   - al volver a arrancar, el bot la reconoce por su número mágico, la sigue vigilando y os avisa al móvil;
   - las señales que seguían abiertas se apuntan en la memoria cuando se cierran (las guarda en
     `MQL5/Files/BotCRT/abiertas_*.bin`).

   Si no puede quedarse encendido, MetaQuotes alquila servidores (VPS) donde dejarlo funcionando, pero son de pago:
   decididlo antes.
9. **La hora del servidor.** Al arrancar, el bot compara la hora del servidor con la de Nueva York (con el reloj del
   ordenador) y, si no cuadra con DesfaseServidorNY, os avisa con el número que hay que poner. Pasa con los brókeres
   que cambian de hora con las fechas europeas: entre el último domingo de octubre y el primero de noviembre (y entre
   el segundo y el último domingo de marzo) van una hora menos. Si avisa, cambiad DesfaseServidorNY esas semanas.

**La rutina:**

- **Los lunes, antes de Londres:** mirad en el panel el sesgo que calcula el bot en cada mercado. Si estáis de acuerdo,
  no toquéis nada. Si no, ponedlo en SesgoDeLaSemana (botón derecho en el gráfico → Asesores expertos → Propiedades →
  Parámetros de entrada). El lunes siguiente, volved a «El que calcula el bot» o ponedlo otra vez.
- **Cada día:** los avisos llegan solos. **No toquéis las operaciones del bot**, ni el stop ni el TP, ni las cerréis a
  mano: lo que se está midiendo es el bot. Si operáis vosotros a mano, apuntadlo en el cuaderno (`cuaderno/`).
- **Los viernes por la tarde, el autoaprendizaje:** doble clic en `Autoaprender.command` (en la carpeta del bot). Repasa
  los precios que el bot exporta cada día, busca sus peores situaciones y le deja las reglas aprendidas; el bot las
  lee solo y os avisa al móvil de lo que ha aprendido y de lo que ha desaprendido. Lo explica `ESTRATEGIA.md`,
  «Autoaprendizaje». La primera vez, el Mac puede pedir permiso para abrirlo (botón derecho → Abrir).
- **Y pasadle a Claude** las memorias (`MQL5/Files/BotCRT/memoria_*.csv`), el informe del autoaprendizaje
  (`informe_autoaprendizaje.txt`) y el cuaderno. Claude os da el informe: qué gana, qué pierde, qué banderas importan,
  qué habría pasado con las descartadas y la psicología.
- **Las demás reglas no se cambian a mitad:** solo con el laboratorio y vuestra aprobación.
- **Para que pueda aprender de muchos meses:** en MT5, Herramientas → Opciones → Gráficos → «Máx. barras en el gráfico»,
  poned «Ilimitado». Si no, MT5 solo da unos años de barras de 15 minutos.
- **Cuánto tiempo:** el autor recomienda al menos 3 meses de demo (unas 60 sesiones). Cuándo se pasa a la cuenta
  propia lo decidís vosotros.

## 1. Instalarlo (una vez)

1. Copiad `BotCRT.mq5` en la carpeta `MQL5/Experts` de MT5. Es la buena si dentro están `Advisors`, `Examples` y
   `Free Robots`.
   - **En Windows:** en MT5, **Archivo → Abrir carpeta de datos** → `MQL5` → `Experts`, y pegadlo ahí.
   - **En Mac:** MT5 funciona dentro de Wine, y la ventana de «Abrir carpeta de datos» es de Wine: no deja soltar
     archivos del Finder. Usad el Finder:
     1. Menú **Ir → Ir a la carpeta…** (Cmd+Mayús+G), pegad
        `~/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files` y pulsad Intro. Si dice
        que no existe, pegad `~/Library/Application Support` y entrad en la carpeta que lleve «metaquotes» o
        «MetaTrader» en el nombre → `drive_c` → `Program Files`.
     2. Entrad en la carpeta de MT5 (`MetaTrader 5` o la del bróker) → `MQL5` → `Experts`.
     3. En la carpeta del bot, seleccionad `BotCRT.mq5` y Cmd+C; en `Experts`, Cmd+V.
   - **Si no encontráis la carpeta:** abrid `BotCRT.mq5` con TextEdit (botón derecho → Abrir con), Cmd+A y Cmd+C. En
     MetaEditor (paso 2): **Archivo → Nuevo → Asesor experto (plantilla)**, nombre `BotCRT`, «Siguiente» hasta
     «Finalizar». En el archivo nuevo, **Edición → Seleccionar todo** y **Edición → Pegar**, y guardad.
2. Abrid MetaEditor: en MT5, **Herramientas → MetaQuotes Language Editor** (o la tecla F4; en Mac, fn+F4).
3. En el panel de la izquierda de MetaEditor, abrid `Experts` → `BotCRT.mq5`.
4. Pulsad **Compilar** (o la tecla F7).
   - Abajo, en la pestaña «Errores», tiene que poner **0 errores**.
   - Los avisos («warnings») no importan.
5. Volved a MT5. En el panel «Navegador», en «Asesores expertos», aparece **BotCRT**. Si no aparece, botón derecho →
   «Actualizar».

## 2. Ponerlo en los cuatro mercados

1. Abrid un gráfico de cada mercado:
   - NASDAQ: según el bróker se llama NAS100, US100 o USTEC;
   - EURUSD;
   - GBPUSD (la libra, añadida el 20-10-2026);
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
- Cuando la operación termina, llega otro aviso con el resultado en R: TP, SL, BE o, con las reglas candidatas, salida
  por 1H, zona de peligro, salida por tiempo o cierre del día. También el cierre del viernes.
- El «1 a 2» del aviso es el ratio de verdad de ese TP: con una regla candidata del objetivo del 4H puede ser otro.
- Si se llega al tope de pérdida del día, llega un aviso (solo uno, aunque el bot esté en los cuatro gráficos) y ese día ya
  no avisa de más entradas.

## 4. Parámetros

| Parámetro | Qué hace | Por defecto |
|---|---|---|
| **Qué hace el bot** | | |
| Modo | «Solo avisos» u «Operar en una cuenta demo». | Solo avisos |
| PermitirCuentaReal | Deja operar en una cuenta real. **No lo activéis** sin hablarlo antes. | No |
| RiesgoPct | Lo que se arriesga en cada operación, en % del balance. Sirve para calcular los lotes. | 1 |
| NombreMercado | El nombre que sale en los avisos y en la memoria. Vacío = el del símbolo. Para que coincida con el Python: NASDAQ, EUR/USD, GBP/USD u Oro (XAU/USD). | vacío |
| **Reglas** | | |
| SesgoDeLaSemana | El sesgo con el que entra: «El que calcula el bot», «Compras», «Ventas» o «Ninguno» (esa semana no entra). Es lo que confirmáis o cambiáis cada lunes. Solo vale para lo que pasa desde que lo ponéis; la historia la repasa siempre con el del bot. | El que calcula el bot |
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
| HoraInicio4H | Hora de Nueva York a la que empiezan las velas de 4H. Decidido el 20-10-2026: 17, es decir, las velas de la 1, las 5 y las 9, en todos los mercados. No lo cambiéis. | 17 |
| **Reglas candidatas** | Apagadas hasta que el laboratorio las pruebe y el equipo las apruebe. | |
| StopAEntradaEnR | Al llegar a +X R, el stop pasa a la entrada. 0 = no. | 0 |
| Vela1Minima | La vela 1 del rango de 4H tiene que ser al menos X veces el tamaño medio de las velas de 4H. 0 = no. | 0 |
| SinNoticias | No entra los días con noticias fuertes. | No |
| EscenariosPermitidos | Solo esos escenarios, por ejemplo `1,2`. Vacío = todos. | vacío |
| Salida1H | Si se forma un rango de 1H en contra: «Salir», o «Stop a la entrada si va ganando; si no, salir». | No |
| TpEnObjetivo4H | El TP va al objetivo del rango de 4H y no a 1 a Ratio. Si queda a menos de 1 R, no entra. | No |
| Exigir1H / Exigir3H | Que el 1H (o el 3H) esté a favor, o que al menos no vaya en contra. | No |
| SoloSinBanderas | Solo situaciones con nota A. | No |
| MaxBanderas | Como mucho tantas banderas rojas: 1 = solo notas A y B. -1 = no. Sale de la prueba con datos reales del 21-10-2026; falta confirmarla. | -1 |
| PausaTrasStops | Tras tantos stops seguidos, el resto del día y el siguiente sin entrar. 0 = no. | 0 |
| ToleranciaDiario | Un rango diario que cierra un poco por fuera (hasta esa parte de la vela 1) sigue valiendo, como hace el autor en el gráfico de futuros. 0 = no. | 0 |
| DiarioValeExpansiva | Tras una vela diaria expansiva a favor (cierra por fuera de la anterior) también vale, con el objetivo en su máximo (en ventas, su mínimo). | No |
| SalidaPeligro | Sale en la «zona de peligro»: ganando, con máximos nuevos en 4H y en 1H (en ventas, mínimos) y una vela de M15 que barre la anterior y cierra dentro. | No |
| NoPerseguir | Si la entrada queda lejos del barrido (stop más grande que una vela media de 4H), no entra y espera otro order block de la misma idea. | No |
| SoloLadoDeLaApertura | Compra solo por debajo de la apertura del día (17:00 de Nueva York) y vende solo por encima. | No |
| AntesDeNoticias | No entra antes de la primera noticia fuerte del día. | No |
| CierreDiario | Cierra lo abierto al final de cada día (17:00 de Nueva York), como en las cuentas de futuros. | No |
| TpHastaObjetivo4H | Si el objetivo del rango de 4H está más lejos que el TP, el TP va hasta él. | No |
| SalidaPorTiempo | Ganando, sale cuando una vela de 4H nueva supera el extremo de la anterior a favor (en compras, un máximo nuevo). | No |
| BreakEvenAntesDeLas9 | Ganando, lleva el stop a la entrada justo antes de la vela de 4H de las 9:00. | No |
| ComprobarObjetivo4H | No entra si el TP queda más allá del objetivo del rango de 4H. | No |
| VetarTomando | No entra con el diario o el 4H tomando máximos (en compras) o mínimos (en ventas). | No |
| IgnorarSesgo / IgnorarDiario | Sin mirar el sesgo de fondo o el diario. Las dos juntas, con MaxOperacionesDia = 3, son el modelo del backtest del autor. Solo para pruebas. | No |
| **Autoaprendizaje** | | |
| UsarReglasAprendidas | Usa las reglas aprendidas (`reglas_aprendidas.txt`): no entra en las situaciones que ha aprendido que pierden. Solo quitan entradas. | Sí |
| ExportarBarras | Al arrancar y una vez al día, guarda los precios de M15 en `barras_ny_<mercado>.csv` para que el bot aprenda. | Sí |
| MesesExportar | Meses de precios que guarda. | 60 |
| **Datos y memoria** | | |
| DesfaseServidorNY | Horas que el reloj del servidor va por delante de Nueva York (ver abajo). | 7 |
| DiferencialFijoPuntos | 0 = usa el diferencial real del bróker. Con un número, usa siempre ese (sirve para comparar con el Python). | 0 |
| MesesHistoria | Meses de historia que repasa al arrancar, para saber cómo está el mercado. | 24 |
| EscribirMemoriaHistorica | Apunta en `historia_<mercado>.csv` lo que habría hecho en esa historia (para comprobarlo con el Python). La memoria en directo no se toca. | No |
| ExportarNoticias | Al arrancar, guarda las noticias fuertes de USD, EUR y GBP en `noticias.csv` para el laboratorio. | No |
| AniosNoticias | Años de noticias que exporta. | 3 |
| NumeroMagico | Número con el que el bot marca sus órdenes. | 20261020 |

**Colchón del stop.** Mirad cuántos decimales tiene el precio en vuestro bróker:

| Mercado | Precio de ejemplo | ColchonStopPuntos | Equivale a |
|---|---|---|---|
| NASDAQ con 1 decimal | 21480.5 | 30 | 3 puntos del índice |
| NASDAQ con 2 decimales | 21480.50 | 300 | 3 puntos del índice |
| EUR/USD | 1.08345 | 10 | 1 pip |
| GBP/USD | 1.26530 | 15 | 1,5 pips (la libra se mueve más) |
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
Reglas aprendidas: 1 · no entra si vela_4h es «vela de las 5»
Última señal: 2026-10-20 10:30 · compra · entrada
```

- **Sesgo de fondo:** lo que el bot calcula con el semanal y el mensual. Es lo que tenéis que confirmar o cambiar cada
  lunes (con SesgoDeLaSemana; entonces el panel dice «Puesto por vosotros» y lo que calcula el bot). Con «sin sesgo» no
  entra.
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
- **Reglas aprendidas:** las situaciones en las que ha aprendido a no entrar (las tres primeras).
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
- El viernes cierra lo que haya abierto: en la cuenta, a las 16:45 de Nueva York (algunos brókeres paran antes de las
  17:00), para no dejarlo abierto durante el parón del fin de semana (con CierreDiario, cada día). Cierra también una
  posición suya que no recuerde. En la memoria lo apunta al cierre de las 17:00, como el Python.
- **Si una orden no entra en la cuenta** (trading algorítmico apagado, stop demasiado cerca para el bróker, sin margen…),
  llega un aviso al móvil que empieza por «NO HA ENTRADO EN LA CUENTA» con el motivo. El bot sigue la operación en su
  memoria igual, para medir la estrategia.
- **Nunca abre dos posiciones** en el mismo mercado: si ya hay una suya en la cuenta, no entra y avisa.
- **Si el bot da por cerrada una operación y en la cuenta sigue abierta** (por ejemplo, el diferencial del bróker era
  distinto), la cierra: la cuenta nunca se queda con una posición que el bot ya no vigila.
- **Tope de pérdida del día:** cada bot deja lo que lleva hoy en una variable global de MT5 (Herramientas → Variables
  globales, las que empiezan por `BotCRT.`) y suma las de los demás. Así el tope vale para todos los mercados juntos.
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
   - DiferencialFijoPuntos con el diferencial de `crt/mercados.py`: NASDAQ con 1 decimal, 15; EUR/USD, 8; GBP/USD, 12; oro, 30;
   - ColchonStopPuntos con el colchón de la tabla;
   - EscribirMemoriaHistorica activado.
3. Pasadle a Claude `historia_<mercado>.csv` (lo que habría hecho en la historia; va aparte para no mezclarse con la
   memoria de lo que hace en directo, que nunca se borra) y las barras. Las dos memorias tienen que tener las mismas
   entradas, salvo en los primeros días, mientras el bot «se pone al día».
