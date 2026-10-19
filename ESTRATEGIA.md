# Estrategia CRT: las reglas del bot

Las reglas salen de seis vídeos del autor de la estrategia (CRT, «Candle Range Theory») y de lo que decidió el equipo el
19-10-2026. El flujo dibujado está en la página https://claude.ai/artifact/MW8eiwC99U2ekSHkywnrfz (privada).

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

## Horario

- Todo va en **hora de Nueva York**, con su cambio de hora.
- El día de trading va de **17:00 a 17:00**. Las velas de 4H empiezan a las 17, 21, **1** (Londres), **5** (pausa de
  Londres), **9** (Nueva York) y 13. La semana cierra el viernes a las 17:00.
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
  vela** si la vela en curso ya ha barrido el mínimo de la anterior, el precio ha vuelto dentro y el marco menor ha
  formado un rango alcista después del barrido (4H con 1H; diario con 4H).
- **Rojo:** el último evento es un rango bajista activo o una ruptura bajista.
- **Ámbar:** el resto. Que un rango bajista se complete **no basta** para comprar: hace falta que se forme el alcista.

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
8. **Topes:** como mucho 2 operaciones por mercado y día, y una operación abierta por mercado a la vez.
9. **Salida:** en el TP o en el stop. Si en una misma barra se tocan los dos, cuenta como stop. Lo que siga abierto el
   viernes a las 17:00 se cierra.

Después de un stop se puede volver a entrar si se forma otra vez todo el setup. Eso es seguir el plan, no venganza.

## Valores provisionales

Son propuestas; se ajustan con la prueba con el pasado:

- espera tras la apertura: 45 minutos;
- horario de entradas: de 1:00 a 13:00 de Nueva York;
- riesgo: 1 % de la cuenta por operación;
- pérdida máxima diaria: 3 % entre los tres mercados (la prueba todavía va mercado a mercado y no la aplica);
- diferencial y colchón del stop de cada mercado: `crt/mercados.py` (valores típicos, no medidos en vuestro bróker);
- un stop más corto que 3 diferenciales no se opera.

## Lo que el bot no copia en la primera versión

Son decisiones que el autor toma a ojo y cambian de un día a otro. La prueba con el pasado puede medirlas una a una.

- Operar contra el sesgo con un objetivo corto cuando 8H, 4H y 1H se alinean al revés.
- Rangos de 8H, 3H o 2H.
- El «failure swing»: barrer un máximo o mínimo anterior que no es el de la vela de antes.
- Entrar con poco y promediar en la entrada ideal.
- Entrar en plena apertura sin esperar al order block (el autor lo dejó de hacer en el sexto vídeo).
- Cerrar antes de tiempo por noticias o porque el precio se para.
- Bajar el riesgo después de un stop.
- Cerrar por partes en cada objetivo.
- Mirar mercados relacionados (índice del dólar, S&P 500).
- Dar más valor a un rango cuya vela 1 es grande.
- La gestión de cuentas de fondeo del autor.

## Lo que todavía no hace

- Avisar al móvil y conectarse a MT5.
- Aplicar la pérdida máxima diaria conjunta de los tres mercados.
- Avisar de las noticias del día (FOMC, NFP…).
