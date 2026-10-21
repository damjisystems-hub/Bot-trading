#!/bin/bash
# Doble clic: el bot CRT repasa todo lo vivido, busca sus peores situaciones y aprende a no entrar en ellas
# (con frenos, ver crt/autoaprendizaje.py). Lee los precios que exporta el bot de MT5 y le deja las reglas
# en su carpeta: el bot las lee solo cada día.
cd "$(dirname "$0")" || exit 1
CARPETA=$(find "$HOME/Library/Application Support" "$HOME/.wine" -type d -path "*MQL5/Files/BotCRT" 2>/dev/null | head -1)
if [ -z "$CARPETA" ]; then
  echo "No encuentro la carpeta del bot en MT5."
  echo "En MT5: Archivo → Abrir carpeta de datos → MQL5 → Files → BotCRT. Arrastrad esa carpeta aquí y pulsad Intro:"
  read -r CARPETA
  CARPETA="${CARPETA%\"}"; CARPETA="${CARPETA#\"}"; CARPETA="${CARPETA% }"
fi
echo "Carpeta del bot: $CARPETA"
echo
python3 autoaprender.py --carpeta "$CARPETA"
echo
read -r -p "Listo. Pulsad Intro para cerrar."
