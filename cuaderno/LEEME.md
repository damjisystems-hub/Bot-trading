# Cuaderno de operaciones

Aquí apuntáis **las operaciones que tomáis vosotros** (en demo, en cuenta propia o en fondeo) y **cómo estabais**.
El bot no puede saber si seguisteis el plan o si entrasteis por venganza: eso solo lo sabéis vosotros. Con el
cuaderno, el informe os dice lo que enseña el vídeo de psicología, pero con vuestros números.

## Cómo apuntar una operación

Abrid `operaciones.csv` con Excel o Numbers y añadid una fila por operación:

| Columna | Qué poner | Ejemplo |
|---|---|---|
| fecha | El día y, si queréis, la hora de Nueva York. | 2026-10-20 10:30 |
| mercado | nasdaq, eurusd, gbpusd u oro. | nasdaq |
| direccion | compra o venta. | compra |
| cuenta | demo, propia o fondeo. | demo |
| siguio_el_plan | si o no. Sed sinceros: es lo que más enseña. | no |
| regla_rota | Si no seguisteis el plan, qué regla os saltasteis. Vacío si lo seguisteis. | entré antes de la apertura |
| emocion | Cómo estabais: calma, dudas, miedo, prisa, venganza, euforia, avaricia (alargar un objetivo ya cumplido), cansancio… | prisa |
| resultado | TP, SL, BE o a mano. | SL |
| r | El resultado en R: 2 es un TP a 1 a 2; -1, un stop; 0, la entrada. | -1 |
| nota | Lo que queráis recordar. | el 1H iba en contra |

Guardad el archivo como CSV (en Excel: «Guardar como» → «CSV UTF-8»).

## El informe

```
python3 cuaderno.py
```

O pasadle el archivo a Claude. El informe cuenta:

- el resultado por cuenta, por emoción, por mercado y siguiendo el plan o no;
- las reglas que más os saltáis y lo que os cuestan;
- los **días bien hechos** (todo siguiendo el plan) frente a los días con algún fallo: el día se califica por el
  proceso, no por el resultado;
- las **ganadas saltándose el plan**: son las más peligrosas, porque enseñan al cerebro a repetir el fallo;
- si después de una pérdida seguís el plan igual que siempre o hay operaciones de venganza;
- la peor racha, los días con demasiadas operaciones y los días que se pasó el tope de pérdida (3 R);
- cuánto tiempo y cuántas operaciones lleváis en cada fase (demo, propia, fondeo). Cuándo se pasa de fase lo decide
  el equipo; el autor estuvo 6 meses en demo y recomienda al menos 3 meses (unas 60 sesiones) haciéndolo todo bien y
  sin emociones.
