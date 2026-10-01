"""Ventana principal (Flet): barra de navegación lateral + vistas."""
from __future__ import annotations

import flet as ft

from app.ui import tema
from app.ui.vista_analisis import VistaAnalisis
from app.ui.vista_carga import VistaCarga
from app.ui.vista_consolidado import VistaConsolidado
from app.ui.vista_estudiantes import VistaEstudiantes
from app.ui.vista_informes import VistaInformes

TITULO = "Gestión de Notas e Informes"


def main(page: ft.Page) -> None:
    page.title = TITULO
    page.theme = tema.crear_tema()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = tema.FONDO
    page.padding = 0
    page.window.width, page.window.height = 1360, 820
    page.window.min_width, page.window.min_height = 1180, 660

    vistas = [VistaEstudiantes(page), VistaCarga(page), VistaConsolidado(page), VistaAnalisis(page),
              VistaInformes(page)]
    contenido = ft.Container(content=vistas[0].control, expand=True,
                             padding=ft.Padding.only(left=28, right=28, top=22, bottom=20))

    def cambiar(e: ft.Event[ft.NavigationRail]) -> None:
        vista = vistas[e.control.selected_index]
        contenido.content = vista.control
        contenido.update()
        vista.al_mostrar()

    rail = ft.NavigationRail(
        selected_index=0, label_type=ft.NavigationRailLabelType.ALL, min_width=104,
        bgcolor=tema.SUPERFICIE, indicator_color=tema.PRIMARIO_SUAVE, on_change=cambiar,
        leading=ft.Container(
            ft.Column([ft.Icon(ft.Icons.SCHOOL_ROUNDED, size=34, color=tema.PRIMARIO),
                       ft.Text("Notas", size=15, weight=ft.FontWeight.W_700, color=tema.TEXTO)],
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            padding=ft.Padding.only(top=18, bottom=18)),
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.GROUPS_OUTLINED, selected_icon=ft.Icons.GROUPS,
                                         label="Estudiantes"),
            ft.NavigationRailDestination(icon=ft.Icons.EDIT_NOTE_OUTLINED, selected_icon=ft.Icons.EDIT_NOTE,
                                         label="Carga de notas"),
            ft.NavigationRailDestination(icon=ft.Icons.FACT_CHECK_OUTLINED, selected_icon=ft.Icons.FACT_CHECK,
                                         label="Consolidado"),
            ft.NavigationRailDestination(icon=ft.Icons.INSIGHTS_OUTLINED, selected_icon=ft.Icons.INSIGHTS,
                                         label="Análisis"),
            ft.NavigationRailDestination(icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION,
                                         label="Informes"),
        ])

    page.add(ft.Row([rail, ft.VerticalDivider(width=1, color=tema.BORDE), contenido],
                    expand=True, spacing=0))
