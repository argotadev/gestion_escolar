"""Punto de entrada: ``python main.py`` (o el .exe generado con build_windows.bat)."""
import sqlite3
from functools import partial

import flet as ft

from app.data.seed import inicializar
from app.ui.main_window import error_inicio, main


def arrancar() -> None:
    try:
        inicializar()      # crea la BD con la estructura escolar si está vacía y prueba que se pueda escribir
    except (sqlite3.Error, OSError) as exc:
        # Sin una base escribible se avisa en vez de dejar cargar datos que no se guardarían.
        ft.run(partial(error_inicio, detalle=str(exc)))
    else:
        ft.run(main)


if __name__ == "__main__":
    arrancar()
