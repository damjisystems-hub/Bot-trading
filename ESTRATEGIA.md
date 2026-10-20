# Estrategia CRT: las reglas del bot

Las reglas salen de doce vídeos del autor de la estrategia (CRT, «Candle Range Theory») y de lo que decidió el equipo
el 19-10-2026. El flujo dibujado está en la página https://claude.ai/artifact/MW8eiwC99U2ekSHkywnrfz (privada).

Si cambia una regla, se cambia aquí, en el código y en su prueba automática.

## Decidido por el equipo (19-10-2026)

| Qué | Decisión |
|---|---|
| Mercados | NASDAQ, EUR/USD y oro (XAU/USD). |
| Tipo de bot | De reglas de velas en varios marcos de tiempo. Primero solo avisa; el equipo decide si entra. |
| Stop y TP | Stop detrás del barrido; TP al doble de esa distancia (1 a 2). |
| Sesgo de fondo | Lo calcula el bot con el mensual, el semanal y el diario; el equipo lo confirma cada lunes. |
| Londres o tras la apertura | El bot avisa en los dos casos y marca cuál es; la prueba con el pasado dirá cuál compensa. |
| Espera tras la apertura | Ninguna entrada en los primeros minutos tras las 9:30 de Nueva York, en los tres mercados. |
| Order block | La vela verde tiene que ser más fuerte que la roja anterior: cuerpo más grande y cierre por encima de donde abrió la roja (en ventas, al revés). |
| Cuentas | Primero demo, luego cuenta propia y después fondeo. |
| Plataformas | MT5 y TradingView. El bot monta sus propias velas, así que los rangos no dependen de la plataforma. |

## Pendiente de decidir

- **A qué hora empiezan vuestras velas de 4H.** En el quinto vídeo son las de la 1, las 5 y las 9 de Nueva York (el día
  empieza a las 17:00, como en MT5). En el vídeo de los 150.000 $ la vela de 4H de la apertura es «la de las 6»: es lo
  que sale en el gráfico de futuros de TradingView, cuyo día empieza a las 18:00 (velas de las 2, las 6 y las 10). En
  el vídeo de los 6.000 $, en cambio, una vela de 4H abre a las 5:00, como en el horario del bot. El bot usa las de las
  17:00 y el laboratorio prueba también las de las 18:00 (`HoraInicio4H` en MT5).
- **Las fechas de los casos del examen** que no la tienen, y confirmar las deducidas (ver `casos/casos.csv`).

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
| entrada lejos del barrido | El stop es más grande que una vela media de 4H. | Vídeo de los stops: «con una mala entrada, si te equivocas es stop directo; con una buena, TP o break even». |

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

**Lo que hace el equipo (cuaderno, `cuaderno/`):** apuntar cada operación propia con si se siguió el plan, la regla que
se saltó y la emoción. El informe del cuaderno califica cada día por el proceso, avisa de las ganadas saltándose el plan
(son las que crean malos hábitos), de las operaciones de venganza tras una pérdida y de los días que se pasó el tope.

**Fases de cuenta** (decidido: demo, propia y fondeo). Cuándo se pasa de una a otra lo decide el equipo. Como
referencia, el autor estuvo 6 meses en demo, se hizo un colchón con lo ganado antes de subir el tamaño, subió poco a poco
y operó sin presión de dinero ni de tiempo. El informe del cuaderno dice cuánto tiempo y cuántas operaciones lleváis en
cada fase y con qué disciplina.

## Valores provisionales

Son propuestas; se ajustan con la prueba con el pasado:

- espera tras la apertura: 45 minutos;
- horario de entradas: de 1:00 a 13:00 de Nueva York;
- riesgo: 1 % de la cuenta por operación;
- tope de pérdida del día: 3 R entre los tres mercados (en MT5, sumados; en la prueba con el pasado, cada mercado solo);
- diferencial y colchón del stop de cada mercado: `crt/mercados.py` (valores típicos, no medidos en vuestro bróker);
- un stop más corto que 3 diferenciales no se opera.

## Lo que el bot no copia

Son decisiones que el autor toma a ojo y cambian de un día a otro. Las que se pueden medir están en el laboratorio como
reglas candidatas.

- Operar contra el sesgo con un objetivo corto cuando 8H, 4H y 1H se alinean al revés (como la venta del vídeo de los
  6.000 $ tras un rango bajista de 4H).
- Rangos de 8H o de 2H.
- El «failure swing»: barrer un máximo o mínimo anterior que no es el de la vela de antes.
- Entrar con poco y promediar en la entrada ideal.
- Entrar en plena apertura sin esperar al order block (el autor lo dejó de hacer en el sexto vídeo).
- Entrar antes de que cierre la vela de M15, o con el order block de M5, cuando el precio va muy rápido (vídeo de la
  única vela).
- Cerrar antes de tiempo por noticias o por ser viernes por la tarde.
- Bajar el riesgo después de un stop.
- Cerrar por partes en cada objetivo.
- Mirar mercados relacionados: el índice del dólar o el S&P 500 (la «SMT» de los vídeos de los stops y de los 6.000 $:
  salir cuando el S&P ya ha tomado su objetivo y el NASDAQ no).
- La gestión de cuentas de fondeo del autor (copiar operaciones en varias cuentas, ir más agresivo en los exámenes).

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
  - velas de 4H del gráfico de futuros (empiezan a las 18:00);
  - diario: también vale tras una vela diaria expansiva a favor, con el objetivo en su máximo («una vela expansiva
    alcista: es muy probable que vayamos a tomar el máximo del día anterior», vídeo de los 6.000 $);
  - salir en la «zona de peligro»: ganando, con máximos nuevos en 4H y en 1H y un barrido en contra en M15 (la
    salida por tiempo del vídeo de los 6.000 $, que salió justo en el máximo).

  Una candidata solo se propone si mejora la media de R por operación en los dos periodos con al menos 30
  operaciones en cada uno.
- **Examen:** `casos/casos.csv` guarda situaciones reales con lo que el bot tenía que hacer: las de los vídeos (35,
  buenas y malas) y las que enseñe el equipo. Un caso suspendido es una pista, no una orden: se mira por qué y, si hace
  falta, se prueba una regla en el laboratorio.
- **Cuaderno:** las operaciones del equipo, para la parte de psicología (ver «Disciplina»).
- **Las reglas solo cambian cuando el equipo lo aprueba.** Se apunta aquí con la fecha y se cambian el código y su
  prueba automática.

## Correcciones del código (20-10-2026)

No cambian las reglas: hacen que el código haga lo que ya decían.

- El verde anticipado ya no vale si la vela en curso ha tomado los dos extremos de la anterior, porque entonces no
  puede cerrar como rango (lo dice la definición de rango).
- Volver a entrar tras un stop cuando la vela de 4H en curso forma otro rango a favor: antes el bot no lo veía mientras
  el rango viejo siguiera activo.

## Lo que todavía no hace

- En la prueba con el pasado, aplicar el tope de pérdida sumando los tres mercados (cada mercado va solo).
- Operar contra el sesgo, usar rangos de 8H o 2H, y las demás cosas de «Lo que el bot no copia».
