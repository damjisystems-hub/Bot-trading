# Bot CRT — guía para agentes (Claude, Codex…)

Guía común para cualquier IA que trabaje en este repositorio. `CLAUDE.md` solo la importa.

- **Habla en español**, claro y sin jerga: el dueño no es programador.
- **Las reglas de la estrategia están en `ESTRATEGIA.md`.** Si cambia una regla, cámbiala allí, en el código y en su
  prueba automática.
- **Las decisiones las toma el equipo.** Si falta una, pregúntala. Si tuviste que suponer algo, dilo al terminar.
- **El bot aprende con método, no solo:**
  - cuando el dueño enseñe una situación (de un vídeo o de lo que le pase), añádela a `casos/casos.csv` con
    mercado, franja en hora de Nueva York y lo que tenía que hacer;
  - un caso suspendido o una idea nueva se prueban en el laboratorio (`aprender.py`) y la regla solo cambia si el
    equipo la aprueba.
- **La memoria del bot de MT5 (`mt5/`) tiene las mismas columnas y los mismos motivos que `crt/memoria.py` y
  `crt/motor.py`:** si cambias uno, cambia el otro.
- **Nada de dinero real** ni de órdenes en cuentas reales sin permiso explícito del dueño. El orden es demo, cuenta
  propia y después fondeo.
- **Resultados honestos:**
  - no presentes resultados con precios inventados como si fueran de la estrategia;
  - las cifras de la prueba con el pasado dependen de los datos y de los costes supuestos (`crt/mercados.py`): dilo
    siempre.
- **Técnica:**
  - Python 3.9 o más nuevo, sin librerías externas (tiene que funcionar en el Mac del dueño sin instalar nada);
  - pruebas: `python3 -m unittest`.
- **Datos fuera de git:** los precios van en `datos/` y los resultados en `resultados/`.
