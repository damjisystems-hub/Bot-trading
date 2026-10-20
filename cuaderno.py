#!/usr/bin/env python3
"""Cuaderno: el informe de las operaciones que apunta el equipo y de lo que le pasaba por la cabeza.

Uso:
  python3 cuaderno.py                       (lee cuaderno/operaciones.csv)
  python3 cuaderno.py otra/ruta.csv

Cómo apuntar cada operación: cuaderno/LEEME.md.
"""

from __future__ import annotations

import sys

from crt import cuaderno


def main() -> int:
    ruta = sys.argv[1] if len(sys.argv) > 1 else "cuaderno/operaciones.csv"
    try:
        apuntes = cuaderno.leer(ruta)
    except ValueError as e:
        print(f"No puedo leer {ruta}: {e}", file=sys.stderr)
        return 1
    print(cuaderno.informe(apuntes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
