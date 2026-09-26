"""Presentación - utilidades compartidas por las vistas."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.data.repository import Curso


def etiqueta_curso(c: Curso) -> str:
    """Texto que se muestra en los desplegables de curso."""
    return f"{c.etiqueta}  ·  {c.orientacion or 'Ciclo Básico'}"


def abrir_archivo(ruta) -> None:
    """Abre un archivo o carpeta con la aplicación predeterminada del sistema."""
    ruta = str(Path(ruta))
    if sys.platform.startswith("win"):
        os.startfile(ruta)                                  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", ruta])
    else:
        subprocess.Popen(["xdg-open", ruta])
