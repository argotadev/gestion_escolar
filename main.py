"""Punto de entrada: ``python main.py`` (o el .exe generado con build_windows.bat)."""
import flet as ft

from app.data.seed import inicializar
from app.ui.main_window import main


def arrancar() -> None:
    inicializar()          # crea la BD con la estructura escolar si está vacía
    ft.run(main)


if __name__ == "__main__":
    arrancar()
