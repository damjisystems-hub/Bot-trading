# Estrategia CRT: las reglas del bot

Las reglas salen de veintitrés vídeos del autor de la estrategia (CRT, «Candle Range Theory») y de lo que decidió el
equipo el 19-10-2026. El flujo dibujado está en la página https://claude.ai/artifact/MW8eiwC99U2ekSHkywnrfz (privada).

Si cambia una regla, se cambia aquí, en el código y en su prueba automática.

## Decidido por el equipo (19-10-2026)

| Qué | Decisión |
|---|---|
| Mercados | NASDAQ, EUR/USD, GBP/USD (añadido el 20-10-2026) y oro (XAU/USD). |
| Tipo de bot | De reglas de velas en varios marcos de tiempo. Primero solo avisa; el equipo decide si entra. |
| Stop y TP | Stop detrás del barrido; TP al doble de esa distancia (1 a 2). |
| Sesgo de fondo | Lo calcula el bot con el mensual, el semanal y el diario; el equipo lo confirma cada lunes. |
| Londres o tras la apertura | El bot avisa en los dos casos y marca cuál es; la prueba con el pasado dirá cuál compensa. |
| Espera tras la apertura | Ninguna entrada en los primeros minutos tras las 9:30 de Nueva York, en todos los mercados. |
| Order block | La vela verde tiene que ser más fuerte que la roja anterior: cuerpo más grande y cierre por encima de donde abrió la roja (en ventas, al revés). |
| Cuentas | Primero demo, luego cuenta propia y después fondeo. |
| Plataformas | MT5 y TradingView. El bot monta sus propias velas, así que los rangos no dependen de la plataforma. |

## Decidido por el equipo (20-10-2026)

| Qué | Decisión |
|---|---|
| Velas de 4H | Las de la 1, las 5 y las 9 de Nueva York (el día de 17:00 a 17:00) en **todos** los mercados, también en el NASDAQ. Es lo que sale en los gráficos de forex de los vídeos («a las 11» abren las de 1H, 2H y 6H, pero no la de 4H) y en el vídeo de los 6.000 $. El laboratorio ya no prueba las de futuros de las 18:00 (las de las 2, las 6 y las 10 del vídeo de los 150.000 $). |
| Fases de cuenta | Se mantiene: demo, cuenta propia y después fondeo, aunque el autor recomienda fondeo primero (vídeos de los 4.500 $, del mejor año y del plan de 0 a 100.000 $). |
| Libra (GBP/USD) | Se añade como cuarto mercado, como la opera el autor (sus noticias fuertes son las de la libra y las del dólar). Para lo demás, se siguen los vídeos. |

## Decidido por el dueño (21-10-2026)

| Qué | Decisión |
|---|---|
| Autoaprendizaje | El bot aprende solo de todas sus situaciones, sobre todo de las peores, y se corrige solo (ver «Autoaprendizaje»). Con frenos: solo puede quitar entradas, una regla tiene que mejorar claramente en tres tramos de tiempo (el último no se usa para buscarla) y lo que deja de cumplirse se desaprende. Las demás reglas las sigue cambiando el equipo. |

## Pendiente de decidir

- **Las fechas de los casos del examen** que no la tienen, y confirmar las deducidas (ver `casos/casos.csv`).
- **El riesgo y el tope del día en las cuentas de futuros**, antes de llegar a esa fase (ver «Disciplina»).
- **Cuándo se pasa de la demo a la cuenta propia** (el autor recomienda al menos 3 meses, unas 60 sesiones).
- **Qué hacer con el resultado de la prueba con datos reales** (abajo): con las reglas de hoy, pierde. El
  autoaprendizaje no lo arreglará si la estrategia no tiene ventaja: solo puede quitar las peores situaciones.

## Prueba con datos reales (21-10-2026)

Primera prueba con precios de verdad: de enero de 2012 a mayo de 2020, con barras de 1 minuto de OANDA (ver
`README.md`, «Datos»). Los costes son los supuestos de `crt/mercados.py`. Son precios de OANDA, no los de vuestro
bróker, y no llegan a 2025: el examen con las situaciones de los vídeos no se ha podido hacer.

| Mercado | Operaciones | Acierto | Resultado | Media por operación |
|---|---|---|---|---|
| EUR/USD | 117 | 35 % | −2,8 R | −0,02 R |
| GBP/USD | 111 | 32 % | −8,9 R | −0,08 R |
| NASDAQ | 99 | 25 % | −24,9 R | −0,25 R |
| Oro | 122 | 30 % | −20,8 R | −0,17 R |
| **Los cuatro juntos** (`cartera.py`) | **449** | **31 %** | **−57,4 R** | **−0,13 R** |

- **Pierde.** A 1 a 2 hay que acertar más del 33 % y acierta el 31 %. La peor caída de los cuatro juntos fue de
  −62 R: con el 1 % por operación, un −62 % de la cuenta.
- **No es por los costes:** sin diferencial seguiría perdiendo (unos −28 R). El diferencial cuesta de 0,04 a 0,08 R por
  operación.
- **El laboratorio no encuentra arreglo:** ninguna de las 35 ideas probadas mejora claramente en los dos periodos (antes
  y después de julio de 2017). Las que mejoran un poco lo hacen en un solo mercado, que es lo que se espera de la suerte.
- **Las banderas rojas parecían avisar:** en 2012–2020 las operaciones con dos o más (nota C) sumaban −55 R en 329, y
  las de nota A o B, −2 R en 120. Pero en los datos de confirmación (abajo) «como mucho una bandera roja» pierde lo
  mismo que sin el filtro: era casualidad.
- **El NASDAQ pierde sobre todo en Londres** (89 de sus 99 operaciones, −24 R). El autor lo opera en la apertura, pero
  en esa franja salen muy pocas operaciones (10) para saber nada.
- El euro y la libra coincidieron abiertos hacia el mismo lado solo 7 veces.

### Por qué pierde: el diagnóstico

- **Un rango de 4H solo no tiene ventaja** (`diagnostico.py`): entrando al cierre de la vela 2, con el stop en el
  barrido y el TP en el objetivo, llega al objetivo entre el 42 % y el 49 % de las veces según el mercado, lo mismo o un
  poco menos que si el precio se moviera al azar, y la media sale entre −0,04 y −0,11 R. Los rangos diarios, igual.
  Cuanto más lejos está el objetivo, menos veces se llega, en la proporción justa del azar.
- **Ningún TP fijo arregla las operaciones del bot:** con lo que llegó a ir a favor cada una, con un TP a 0,5, 1, 1,5 o
  2 R la media sigue en 0 o por debajo en los cuatro mercados.
- **Los stops más pegados del autor tampoco:** se probaron aparte el stop en el order block de M15 y en el barrido de
  1H, con el TP a 1 a 2 o en el objetivo del 4H. La mejor versión (stop en el barrido de 1H y TP en el objetivo del 4H)
  perdía −13 R en 246 operaciones en 2012–2020 y −46,5 R en 207 en 2005–2011. No se ha añadido al bot.
- **No es por la forma de contar:** ninguna operación tocó el stop y el TP en la misma barra de 15 minutos, así que contar
  el stop en ese caso no perjudica.

### Confirmación con otros años (2005–2011)

Los datos de 2005 a 2011 (del oro, desde 2006) se guardaron sin mirar para confirmar al final. Con ellos:

| 2005–2011 | Operaciones | Acierto | Resultado | Media por operación |
|---|---|---|---|---|
| Las reglas de hoy | 368 | 31 % | −40,1 R | −0,11 R |
| Como mucho una bandera roja | 106 | 32 % | −11,8 R | −0,11 R |
| Stop en el barrido de 1H y TP en el objetivo del 4H | 207 | 29 % | −46,5 R | −0,22 R |

En total, de 2005 a 2020: **817 operaciones y unos −97 R** con las reglas de hoy. Con los datos que hay, la
estrategia, tal como está escrita en este documento, no gana en ninguno de los dos tramos. Para repetirlo con otros
datos: `python3 aprender.py <datos> --mercado <m> --confirmar <otros datos>`.

### Años recientes: 2021–2026, con los precios de la demo (22-10-2026)

Barras de 15 minutos de la cuenta demo de MetaQuotes, exportadas por el bot de MT5 (`barras_ny_*.csv`, ya en hora de
Nueva York: comprobado con la apertura de cada semana). Van del 19-09-2021 (el NASDAQ, del 06-07-2022) al 21-10-2026.
Los costes son los supuestos de `crt/mercados.py`.

| Hasta el 31-12-2025 | Operaciones | Acierto | Resultado | Media por operación |
|---|---|---|---|---|
| EUR/USD | 69 | 26 % | −14,6 R | −0,21 R |
| GBP/USD | 84 | 40 % | +10,5 R | +0,12 R |
| Oro | 54 | 33 % | −4,1 R | −0,08 R |
| NASDAQ | 41 | 34 % | −0,4 R | −0,01 R |
| **Los cuatro juntos** (`cartera.py`) | **248** | **34 %** | **−8,6 R** | **−0,03 R** |

- **Pierde poco, pero pierde.** La peor caída de los cuatro juntos fue de −27 R. En 2026 (enero a octubre) va peor:
  53 operaciones, 25 % de acierto y −12,8 R.
- **Sin costes daría +8,4 R** (+0,03 R por operación), que es casi cero: el diferencial, unos 0,06 R por operación, lo
  deja en pérdidas.
- **La libra gana, pero dentro de lo que da la suerte** (±13 R en 84 operaciones), y en 2012–2020 perdió −8,9 R.
- **Los rangos de 4H en bruto** llegan a su objetivo del 43 al 46 % de las veces, un poco menos que al azar (46–48 %),
  igual que en 2005–2020.
- **Lo que parece ir bien cambia de signo de un periodo a otro:** las entradas de la vela de la 1 ganan +20 R ahora y
  perdieron −44 R y −31 R antes; las de nota C ganan +12 R ahora y perdieron −30 R y −55 R antes. Es suerte, no una regla.
- **Laboratorio** (36 ideas, en dos periodos): ninguna mejora clara en ningún mercado, así que no hay nada que confirmar
  con 2012–2020. **El autoaprendizaje** no aprende nada.
- **Examen con los vídeos (el primero con precios de esas fechas):** de 32 situaciones con fecha, el bot hace lo mismo
  que el autor en 8. De las 24 que no: en 12 el bot no vio un order block con el 4H a favor, en 9 no tenía sesgo a favor
  (el semanal y el mensual en contra) y en 3 el diario no estaba a favor. Algunas fechas y pares están deducidos.

**De 2005 a 2025, unas 1.065 operaciones y unos −106 R.** No gana en ningún tramo.

**Lo que se puede hacer (lo decide el equipo):**

1. ~~Probar con años recientes~~: hecho (arriba): también pierde.
2. Seguir en demo solo para medir, sin esperar que gane, y revisar las reglas con lo que salga. Con dinero real no tiene
   sentido mientras pierda en el pasado.
3. Revisar con el autor o con vuestra experiencia en qué se diferencia el bot de lo que hace él a ojo (ver «Lo que el
   bot no copia»): si la estrategia gana, la ventaja tiene que estar justo ahí, porque el patrón solo no la tiene. El
   examen dice por dónde empezar: el order block con el 4H a favor y el sesgo.

## Copiar al autor sin engañarnos (empezado el 22-10-2026)

El equipo decidió el 22-10-2026 empezar por que el bot haga lo que hace el autor: «potenciar al máximo, pero sin
autoengañarse». Estas reglas se fijaron **antes** de mirar los casos:

1. **Casos de búsqueda y casos guardados.**
   - Búsqueda (19): los casos con fecha del euro y de la libra y el del NASDAQ del 17-11-2025. Se miran vela a vela para
     ver en qué se diferencia el bot del autor.
   - Guardados (13): los del NASDAQ de 2026 (tercer vídeo, vídeo de los 150.000 $ y vídeo de «la única vela»). No se
     miran hasta el final: sirven para comprobar si las correcciones valen fuera de donde se buscaron.
2. **Solo se cambia lo que dice el autor.** Cada corrección tiene que salir de sus palabras en los vídeos, no de lo que
   haga pasar un caso. Se programa como regla candidata, apagada: el equipo decide si se enciende.
3. **Se mide si hace lo mismo que el autor, no si gana.** En cada caso se mira si el bot compra, vende o no entra como
   él. Los casos del vídeo del backtest se examinan con su modelo (sin sesgo ni diario), como dijo que lo hacía.
4. **La prueba de dinero, una sola vez y al final**, en los tres tramos (2005–2011, 2012–2020 y 2021–2025), con 2026
   aparte:
   - la corrección **mejora** solo si sube la media por operación en los tres tramos;
   - **gana** solo si la media es positiva en los tres tramos y, en total, por más de dos errores típicos;
   - después de verla, no se retoca.

**Un descuido, contado:** el 22-10 se leyó por error la transcripción del vídeo de «la única vela» (sin mirar sus
precios). Por limpieza, su caso pasa a búsqueda: quedan 20 de búsqueda y 12 guardados (el tercer vídeo y el de los
150.000 $). Las transcripciones de esos dos vídeos no se leen hasta el final.

**Punto de partida (reglas de hoy, precios de la demo):**
- búsqueda: 7 de 20 bien; de los 16 casos en los que el autor entra, el bot entra igual en 3;
- guardados: 3 de 12 bien; de los 9 en los que el autor entra, el bot entra igual en ninguno;
- los casos en los que el autor no entra los acierta todos, pero solo porque el bot casi nunca entra.

## Horario

- Todo va en **hora de Nueva York**, con su cambio de hora.
- El día de trading va de **17:00 a 17:00**. Las velas de 4H empiezan a las 17, 21, **1** (Londres), **5** (pausa de
  Londres), **9** (Nueva York) y 13. Las de 3H, a las 17, 20, 23, 2, 5, **8**, 11 y 14. La semana cierra el viernes a
  las 17:00.
- En España suele ser 6 horas más (las 9:30 de Nueva York son las 15:30), salvo un par de semanas al año.

## Qué es un rango (igual en todos los marcos)

Se comparan dos velas seguidas del mismo marco, la vela 1 y la vela 2:

- **Rango alcista:** la vela 2 toma el mínimo de la vela 1 y vuelve a cerrar dentro. Objetivo: el máximo de la vela 1.
  El mínimo de la vela 2 es el **barrido** («turtle soup»).
- **Rango bajista:** lo mismo al revés.
- **Ruptura:** la vela 2 cierra por fuera de la vela 1. No es un rango: se espera que el precio siga en esa dirección.
- Si la vela 2 no toma ningún extremo, o toma los dos y cierra dentro, no cuenta.
- Un rango se **completa** cuando el precio toca su objetivo y se **anula** cuando una vela de su marco cierra con el
  cuerpo más allá del barrido. Una mecha no lo anula.

## El semáforo de cada marco

Para operar en una dirección (el ejemplo es de compras):

- **Verde:** el último evento es un rango alcista que sigue activo. También se pone en verde **antes de que cierre la
  vela** si la vela en curso ya ha barrido el mínimo de la anterior sin haber tomado su máximo, el precio ha vuelto
  dentro y el marco menor ha formado un rango alcista después del barrido (4H con 1H; diario con 4H).
- **Rojo:** el último evento es un rango bajista activo o una ruptura bajista.
- **Ámbar:** el resto. Que un rango bajista se complete **no basta** para comprar: hace falta que se forme el alcista.

El bot mira también el 3H y el 1H. No hace falta que estén en verde para entrar, pero si van en contra es una bandera
roja (ver más abajo) y el laboratorio prueba exigirlos.

## Sesgo de fondo (cómo lo calcula el bot)

- Del semanal y del mensual se mira el último evento: un rango activo empuja hacia su objetivo y una ruptura, en su
  dirección. Un rango completado o anulado ya no empuja.
- Manda el semanal. Si el semanal no dice nada, el mensual. Si se contradicen, no hay sesgo y no se opera.
- En la prueba con el pasado se usa el sesgo calculado. En real, el equipo lo confirma o lo cambia cada lunes.

## Una entrada, paso a paso

El bot lo comprueba al cierre de cada barra de 15 minutos:

1. **Horario:** entre la 1:00 y las 13:00 de Nueva York, y ninguna entrada entre las 9:30 y las 10:15.
2. **Sesgo de fondo** a favor.
3. **Order block de M15** a favor, tal como está decidido arriba. Se entra al cierre de esa vela.
4. **Diario en verde** (un rango diario a favor, cerrado o anticipado con el 4H).
5. **4H en verde** (al cierre de la vela, o antes con 1H).
6. Solo cuenta **el primer order block** de cada idea, después de que el 4H se ponga en verde. Si no aparece, no se
   entra.
7. **Stop** detrás del barrido de 4H, con un pequeño colchón. **TP** al doble de lo que se arriesga. Si el TP queda más
   allá del objetivo del diario, no se entra.
8. **Topes:** como mucho 2 operaciones por mercado y día, una operación abierta por mercado a la vez y el tope de
   pérdida del día (ver «Disciplina»).
9. **Salida:** en el TP o en el stop. Si en una misma barra se tocan los dos, cuenta como stop. Lo que siga abierto el
   viernes a las 17:00 se cierra.

**Volver a entrar después de un stop** es seguir el plan, no venganza, si se forma otra vez todo el setup (segundo
vídeo y vídeo de los stops: «me saca, reacciona, vuelve a hacer un rango de 4H, un order block… y vuelvo a entrar»).
El bot lo hace así: si la idea de 4H ya dio su entrada y la vela de 4H en curso está formando otro rango a favor (por
ejemplo, tras barrer el stop), es una idea nueva y vuelve a buscar su primer order block.

## Banderas rojas y nota de cada situación

Son las cosas que el autor no quiere ver al entrar. **No impiden entrar**: el bot las apunta en la memoria y en el aviso,
y el aprendizaje mide si las operaciones que las llevan pierden más.

| Bandera | Qué es | De dónde sale |
|---|---|---|
| el diario va en contra | El diario solo está en verde anticipado y lo cerrado va en contra (un rango diario en contra). | Vídeo de los stops (lunes y viernes). |
| el diario está tomando máximos / mínimos | La vela diaria en curso ya pasó el extremo de ayer hacia el lado de la operación: puede formar un rango diario en contra. | Vídeo de los stops («no quieres comprar mientras estamos tomando máximos»). |
| el 4H está tomando máximos / mínimos | Lo mismo en 4H. | Vídeos de la única vela, de los 150.000 $ y cuarto vídeo («si está abriendo por arriba, nos crea rangos bajistas»). |
| el 3H va en contra | El último evento del 3H es un rango activo o una ruptura en contra. | Vídeo de los 150.000 $ (4H, 3H y 1H alineados). |
| el 1H va en contra | Lo mismo en 1H. | Vídeos de los stops y de los 150.000 $. |
| justo antes de la apertura | Entrada entre las 9:00 y las 9:30. | Vídeo de los stops: el stop del martes; «mi acierto mejora mucho cuando ya ha pasado la apertura». |
| entrada lejos del barrido | El stop es más grande que una vela media de 4H. | Vídeo de los stops: «con una mala entrada, si te equivocas es stop directo; con una buena, TP o break even». Vídeo de las pruebas de fondeo: «nunca entréis persiguiendo el precio cuando está tan lejos». |
| el 1H está tomando máximos / mínimos | Lo mismo en 1H. | Vídeo del paso a paso: «la nueva vela de 1H abre por arriba… otra red flag». |
| compra por encima / venta por debajo de la apertura del día | En compras, el precio ya está por encima de donde abrió el día (17:00 de Nueva York); en ventas, por debajo. | Vídeo de la estrategia simple: «quieres vender por encima de la apertura diaria». |

**Nota:** A sin banderas, B con una, C con dos o más. El informe de aprendizaje separa los resultados por nota y por
bandera.

## Disciplina y psicología

Del vídeo de los 5 años de psicología y del de «+100k al año». La estrategia no siempre es el problema: muchas veces está
en la cabeza.

**Lo que hace el bot:**

- **Tope de pérdida del día** (el «bloqueador externo» que recomienda el vídeo): al perder 3 R en un día (el 3 % con el 1 %
  por operación), ese día ya no entra. El bot de MT5 suma los mercados en los que está puesto, avisa una vez y os dice
  que cerréis el gráfico. La prueba con el pasado va mercado a mercado y lo aplica a cada uno.
- **Riesgo fijo:** siempre el mismo % por operación, vengáis de ganar o de perder. Cada operación es independiente de las
  anteriores («la mentira de las rachas»).
- **Racha de stops** en el panel y, a partir de 3, el consejo de parar un día. La pausa automática es una regla
  candidata.
- **Proceso antes que resultado:** el informe cuenta las «pérdidas buenas» (nota A: se hizo todo bien y salió mal), la
  racha de stops que es normal con el acierto que hay y si una operación influye en la siguiente.
- El stop no se mueve más allá de donde se invalida la idea, ni se cierra antes de tiempo por miedo: solo lo que diga una
  regla aprobada.
- Cuando el objetivo se cumple, se cierra: alargarlo es avaricia. En el vídeo de los 6.000 $ el autor lo cuenta de una
  venta suya: habría sido TP, quiso apurar más y acabó casi sin ganar. El bot nunca alarga su TP.
- **El riesgo no cambia tampoco cuando se va perdiendo** (vídeos de las pruebas de fondeo y del plan de 0 a 100.000 $):
  «decidí dejar siempre el riesgo fijo al 1 % y si lo tengo que recuperar, lo voy a recuperar también al 1 %». Bajarlo
  tras perder hace que se pierda rápido y se recupere lento, y cambiarlo «arruina la probabilidad».
- **Stops buenos y stops malos** (vídeo del backtest): un stop con la lógica bien hecha «no pasa nada, bienvenido sea y a
  seguir»; lo que no se puede permitir son los malos, los que llegan por saltarse el plan. El bot los separa con la nota.
- **Paciencia, sin objetivo de dinero** (curso desde 0): a veces hay que pasar «3 o 4 horas sin pulsar ningún botón», y
  ponerse un objetivo del día («hoy voy a ganar 2.000 $») lleva a forzar operaciones. La prisa por pasar cuentas fue su
  peor enemigo. El bot no tiene objetivo de dinero: solo entra cuando sale la situación.
- **Coherencia en las salidas** (vídeo de las salidas): «si jugamos conservadores, jugamos conservadores para todo», sin
  quejarse cuando el precio sigue sin nosotros. Lo que dice cuál compensa es contar las veces: el laboratorio compara
  cada salida candidata con las mismas operaciones.
- **El tope del día y las cuentas de futuros.** En el vídeo de los 4.500 $ perder un 3 % en un día es «hacer el tonto»
  («si ayer me llego a quedar con la primera pérdida del -1…»). Y en el de «¿Me paso a futuros?» el tope total de una
  cuenta de futuros es de un 3–4 % y sube con el saldo. Con el 1 % por operación, un día con el tope de 3 R se llevaría
  casi toda una cuenta así. Antes de pasar a fondeo de futuros hay que decidir el riesgo y el tope (el laboratorio ya
  prueba el de 1 R).

**Lo que hace el equipo (cuaderno, `cuaderno/`):** apuntar cada operación propia con si se siguió el plan, la regla que
se saltó y la emoción. El informe del cuaderno califica cada día por el proceso, avisa de las ganadas saltándose el plan
(son las que crean malos hábitos), de las operaciones de venganza tras una pérdida y de los días que se pasó el tope.

**Fases de cuenta** (decidido y confirmado el 20-10-2026: demo, propia y fondeo, aunque el autor recomienda fondeo
primero).
Cuándo se pasa de una a otra lo decide el equipo. Como referencia:

- el autor estuvo 6 meses en demo, se hizo un colchón con lo ganado antes de subir el tamaño, subió poco a poco y operó
  sin presión de dinero ni de tiempo;
- en el plan de 0 a 100.000 $ recomienda al menos 3 meses de demo (unas 60 sesiones) con Londres y Nueva York, hasta que
  «sin emociones haces todo perfecto», y una hora al día de prueba con el pasado «para ganar confianza»;
- de la demo saca qué días y qué velas le van mejor («si ves que la vela de las nueve es la que se te da mejor…»): el
  informe de aprendizaje separa las operaciones por día y por vela de 4H de la entrada;
- para escalar, empezar con cuentas pequeñas y no saltarse escalones («no paséis de 5 a 50»).

El informe del cuaderno dice cuánto tiempo y cuántas operaciones lleváis en cada fase y con qué disciplina.

## Valores provisionales

Son propuestas; se ajustan con la prueba con el pasado:

- espera tras la apertura: 45 minutos;
- horario de entradas: de 1:00 a 13:00 de Nueva York (en forex el autor empieza a las 2:30, «antes de eso nunca», y da
  la sesión por terminada a las 11: el laboratorio prueba las dos cosas);
- riesgo: 1 % de la cuenta por operación;
- tope de pérdida del día: 3 R entre todos los mercados (en MT5, sumados; en la prueba con el pasado, cada mercado solo);
- diferencial y colchón de la libra: un poco más que los del euro, porque se mueve más (valores típicos, no medidos);
- diferencial y colchón del stop de cada mercado: `crt/mercados.py` (valores típicos, no medidos en vuestro bróker);
- un stop más corto que 3 diferenciales no se opera.

## Lo que el bot no copia

Son decisiones que el autor toma a ojo y cambian de un día a otro. Las que se pueden medir están en el laboratorio como
reglas candidatas.

- Operar contra el sesgo con un objetivo corto cuando 8H, 4H y 1H se alinean al revés (como la venta del vídeo de los
  6.000 $ tras un rango bajista de 4H).
- Rangos de 8H o de 2H, y salidas por tiempo con velas de 2H o de 6H (vídeo de las salidas). El bot hace la de 4H.
- El «failure swing»: barrer un máximo o mínimo anterior que no es el de la vela de antes.
- Seguir con un rango de 1H cuando el de 4H ya dio su entrada y queda el objetivo diario (el miércoles del paso a paso).
- Cambiar el sesgo dentro de la semana: completado el objetivo semanal, usar el diario hasta el viernes (paso a paso).
- Entrar con poco y promediar en la entrada ideal, o recargar con la cuenta propia (vídeo de los 4.500 $).
- Entrar en plena apertura sin esperar al order block (el autor lo dejó de hacer en el sexto vídeo).
- Entrar antes de que cierre la vela de M15, o con el order block de M5, cuando el precio va muy rápido (vídeo de la
  única vela), o antes de que cierre un order block muy grande (vídeo del backtest).
- Operar en Asia: la entrada ideal del 2 de enero (vídeo de la única estrategia para 2026) estaba fuera del horario.
- Cerrar antes de tiempo por noticias o por ser viernes por la tarde.
- Bajar el riesgo después de un stop.
- Cerrar por partes en cada objetivo, o en la salida por tiempo dejando un 10–20 % hasta el objetivo (vídeo de las
  salidas). El bot cierra entera.
- Alargar más allá del objetivo con la salida por tiempo de 1H (vídeo de las salidas): choca con no alargar el TP.
- Ajustar el stop según la cuenta, o apretarlo para que salga 1 a 2 cuando el objetivo está cerca (vídeos de las
  pruebas de fondeo y del paso a paso). El bot lo deja siempre detrás del barrido, y la regla candidata del objetivo
  del 4H no entra si el TP no cabe.
- Mirar mercados relacionados: el índice del dólar, la libra o el S&P 500 (la «SMT» de los vídeos de los stops, de los
  6.000 $, del curso desde 0 y de las pruebas de fondeo: salir cuando el otro mercado ya ha tomado su objetivo y este
  no, o ver un rango que solo existe en uno de los dos). Aunque el bot ya opera el euro y la libra, cada mercado va por
  su lado. Por eso la venta de la libra del 7-10-2025 (vídeo de las pruebas de fondeo), cuyo rango solo existía por la
  SMT con el euro y que entró de noche, no está en el examen.
- La gestión de cuentas de fondeo del autor: copiar operaciones en varias cuentas, subir el riesgo en los exámenes (un
  2–3 %, o el 1 % hasta el +4 % y luego lo que falte de una vez) y buscar 1 a 3 en ellos.

## Cómo aprende el bot (y quién cambia las reglas)

- **Memoria:** apunta cada situación que ve.
  - Es la primera vez que una idea de 4H da un order block en horario, se tome o no, o es una entrada.
  - Guarda la decisión y su motivo, y el contexto:
    - sesión, día y escenario;
    - sesgo semanal y mensual;
    - cómo se puso en verde el diario y el 4H, y cómo estaban el 3H y el 1H;
    - tamaño de la vela 1 y del stop;
    - distancia al objetivo diario;
    - noticias;
    - banderas rojas y nota.
  - Guarda también el resultado y hasta dónde llegó a favor y en contra.
  - Las descartadas se siguen como operaciones fantasma hasta su stop o su TP.
  - El bot de MT5 escribe la misma memoria en directo.
- **Laboratorio:** prueba las reglas candidatas en dos periodos:
  - 1 a 1;
  - distintas esperas tras la apertura;
  - solo después de la apertura, o solo en Londres;
  - diario menos exigente;
  - stop a la entrada al llegar a +1 R;
  - solo rangos con la vela 1 grande;
  - sin el escenario 3;
  - una operación al día;
  - no operar los días de noticias;
  - salir, o llevar el stop a la entrada, si se forma un rango de 1H en contra (la «salida por tiempo» y la lección del
    viernes del vídeo de los stops);
  - TP en el objetivo del rango de 4H («en fondeo solo voy a por los primeros objetivos»);
  - exigir el 1H a favor, o al menos que no vaya en contra, y exigir el 3H a favor (vídeos de los 150.000 $ y de la
    única vela);
  - solo situaciones sin banderas rojas;
  - dejar el día al perder 1 R, y un día de pausa tras 3 stops seguidos (vídeo de psicología);
  - rango diario aunque cierre un poco por fuera (vídeo de la única vela);
  - diario: también vale tras una vela diaria expansiva a favor, con el objetivo en su máximo («una vela expansiva
    alcista: es muy probable que vayamos a tomar el máximo del día anterior», vídeo de los 6.000 $);
  - salir en la «zona de peligro»: ganando, con máximos nuevos en 4H y en 1H y un barrido en contra en M15 (la
    salida por tiempo del vídeo de los 6.000 $, que salió justo en el máximo);
  - no perseguir: si la entrada queda lejos del barrido, no entrar y esperar otro order block de la misma idea («nunca
    entréis persiguiendo el precio», vídeo de las pruebas de fondeo);
  - comprar solo por debajo de la apertura del día y vender solo por encima (vídeo de la estrategia simple);
  - entradas solo hasta las 11:00 (curso desde 0) o solo desde las 2:30 (vídeo del backtest);
  - no entrar antes de la primera noticia fuerte del día: «el precio no tiene por qué llegar a ningún sitio si va a
    llegar con la noticia» (curso desde 0);
  - cerrar lo abierto al final del día, a las 17:00, como en el «day trading» y en las cuentas de futuros (curso desde
    0);
  - si el objetivo del 4H está más lejos que el TP, dejar correr hasta él: «al menos ratio 2 o el objetivo final» (vídeo
    de la estrategia simple);
  - la salida por tiempo: ganando, salir cuando una vela de 4H nueva hace un máximo nuevo (en ventas, un mínimo), porque
    puede formar un rango al revés (vídeo de las salidas);
  - ganando, stop a la entrada justo antes de la vela de 4H de las 9:00, porque «es muy probable que vaya a hacer el
    nuevo alto» (vídeo del backtest);
  - hasta 3 operaciones al día, y que el TP quepa antes del objetivo del 4H: «no vamos a querer tomar un trade de ratio
    uno» (vídeo del backtest);
  - no entrar con el diario o el 4H tomando a favor: «nunca estar vendiendo tras tomar bajos» (vídeo de la única
    estrategia para 2026);
  - el modelo del backtest del autor, para comparar: sin sesgo ni diario y hasta 3 operaciones al día (su «+80 %» son
    11 TP de 13 operaciones en una semana de mayo de 2025, elegida después de verla);
  - como mucho una bandera roja (nota A o B), que salió de la prueba con datos reales del 21-10-2026 y no se confirmó
    con los años 2005–2011.

  Una candidata solo se propone si mejora la media de R por operación en los dos periodos, con al menos 30
  operaciones en cada uno y por más de un «error típico» (lo que baila la media por pura suerte con esas operaciones).
  Con tantas ideas a prueba, alguna mejoraría en los dos periodos por casualidad: por eso no basta con mejorar. «Solo en Londres» y «solo después de la apertura» se miran en cada mercado: el autor opera
  el forex en Londres y el NASDAQ en la apertura (vídeo «¿Me paso a futuros?»), aunque en otros vídeos compra el NASDAQ
  en Londres.
- **Examen:** `casos/casos.csv` guarda situaciones reales con lo que el bot tenía que hacer: las de los vídeos (60,
  buenas y malas, 4 de ellas de la libra) y las que enseñe el equipo. Un caso suspendido es una pista, no una orden: se mira por qué y, si hace
  falta, se prueba una regla en el laboratorio. Los diez días del backtest del autor son de su modelo sin sesgo ni
  diario: se examinan con `python3 examen.py --modelo-del-backtest`.
- **Cuaderno:** las operaciones del equipo, para la parte de psicología (ver «Disciplina»).
- **Autoaprendizaje** (ver abajo): las reglas aprendidas («no entrar si…») las añade y las quita el propio bot.
- **Las demás reglas solo cambian cuando el equipo lo aprueba.** Se apunta aquí con la fecha y se cambian el código y su
  prueba automática.

## Autoaprendizaje

El bot aprende solo de todo lo que le pasa, sobre todo de lo peor (decidido por el dueño el 21-10-2026):

1. **El bot de MT5 exporta sus precios cada día** (`barras_ny_<mercado>.csv`, en su carpeta `MQL5/Files/BotCRT`). Ahí
   está todo lo vivido, también lo que ha hecho en directo.
2. **Autoaprender** (doble clic en `Autoaprender.command` en el Mac, o `python3 autoaprender.py --carpeta …`) repasa todo
   con el bot entero y busca sus **peores situaciones**: para cada cosa que describe una situación, cuánto pierden de
   media las operaciones que la tenían. Son las mismas cosas que la memoria:
   - dirección, sesión y vela de 4H de la entrada;
   - día de la semana;
   - sesgo semanal y mensual;
   - diario y cómo se puso en verde;
   - cómo se puso en verde el 4H;
   - 3H, 1H y escenario;
   - nota y cada bandera roja.
3. **Cada una de las peores es una idea:** «no entrar en esa situación». La prueba con el bot entero.
4. **Los frenos**, para no aprender la suerte (ya pasó con lo de las banderas):
   - los precios se parten en tres tramos de tiempo iguales; las peores situaciones se buscan solo en los dos primeros
     y el tercero se guarda para confirmar;
   - una regla se aprende solo si mejora claramente (más que un «error típico») en los tres tramos y deja al menos
     30 operaciones en cada uno; si se aprenden varias, también tienen que mejorar todas a la vez;
   - solo quita entradas: nunca añade riesgo;
   - cada vez se empieza de cero: lo que con los datos nuevos ya no se cumple se **desaprende**.
5. **Lo aprendido va a `reglas_aprendidas.txt`**, con la fecha y las pruebas. El bot de MT5 lo lee cada día, deja de
   entrar en esas situaciones (motivo «regla aprendida» en la memoria) y avisa al móvil de lo que ha aprendido y de lo
   que ha desaprendido. Se puede apagar con UsarReglasAprendidas.

Con pocos datos no aprende nada, y es lo correcto: hacen falta muchas operaciones para distinguir una situación mala de
la mala suerte. Cuantos más meses de precios exporte el bot (MesesExportar), antes podrá aprender.

**Primera vuelta (21-10-2026), con los precios de OANDA de 2005 a 2020:** no ha aprendido nada en ninguno de los cuatro
mercados. Las situaciones que más pierden en los dos primeros tramos no mejoran claramente en el tercero, o dejan menos
de 30 operaciones por tramo. Por ejemplo, en el EUR/USD «no entrar en Londres» mejoraba en los tres tramos, pero con
15–23 operaciones por tramo. Es lo que se espera si la estrategia no tiene ventaja: quitar sus peores situaciones no la
convierte en ganadora.

## Correcciones del código (20-10-2026)

No cambian las reglas: hacen que el código haga lo que ya decían.

- El verde anticipado ya no vale si la vela en curso ha tomado los dos extremos de la anterior, porque entonces no
  puede cerrar como rango (lo dice la definición de rango).
- Volver a entrar tras un stop cuando la vela de 4H en curso forma otro rango a favor: antes el bot no lo veía mientras
  el rango viejo siguiera activo.
- Bot de MT5 en vivo: la barra que acaba a las 17:00 se procesa cuando llega la siguiente, y en NASDAQ y oro eso es tras
  el parón (el viernes, el domingo por la noche). La posición de la cuenta demo se quedaba abierta todo el fin de
  semana. Ahora se cierra a las 16:45 de Nueva York; la memoria la sigue apuntando al cierre de la barra, como el Python.
- El aviso al móvil ponía siempre «1 a 2», aunque el TP estuviera en otro sitio por una regla candidata. Ahora pone el
  ratio de verdad.

## Correcciones del código (21-10-2026)

Salen de dos revisiones a fondo del código (una del bot de MT5 y otra comparando el Python con el MT5). Con los mismos
precios, los dos bots deciden igual.

- **Barras de fin de semana:** algunos datos traen barras de los domingos antes de la apertura o de los viernes después
  del cierre. Formaban velas diarias y semanales falsas y cambiaban el sesgo. Ahora se quitan, en los dos bots.
- **El diario anticipado:** un rango de 4H viejo, formado antes del barrido del diario, tapaba el rango de 4H que se
  estaba formando después, y el diario no se ponía en verde. Es el mismo fallo que el de volver a entrar tras un stop.
- **Lectura de datos:** la hora local de Dukascopy («GMT+0100») se leía como UTC, y un CSV en UTC con la fecha y la hora
  en columnas separadas se tomaba por uno de MT5.
- **Un tope de pérdida o una vela 1 mínima de 0** querían decir cosas distintas en cada bot. Ahora, en los dos, 0 es
  «apagado».
- **Bot de MT5 en directo** (versión 1.15):
  - al reiniciar MT5 reconoce su posición en la cuenta y las señales que seguían abiertas;
  - avisa al móvil si una orden no entra;
  - nunca abre dos posiciones en el mismo mercado;
  - cierra en la cuenta lo que él da por cerrado;
  - redondea el stop y el TP al salto del símbolo;
  - comprueba la hora del servidor;
  - guarda la historia aparte de la memoria en directo.

## Lo que todavía no hace

- Operar contra el sesgo, usar rangos de 8H o 2H, y las demás cosas de «Lo que el bot no copia».
