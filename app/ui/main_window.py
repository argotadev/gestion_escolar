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

    # (ícono, ícono seleccionado, nombre) de cada vista, en el orden de ``vistas``
    secciones = [
        (ft.Icons.GROUPS_OUTLINED, ft.Icons.GROUPS, "Estudiantes"),
        (ft.Icons.EDIT_NOTE_OUTLINED, ft.Icons.EDIT_NOTE, "Carga de notas"),
        (ft.Icons.FACT_CHECK_OUTLINED, ft.Icons.FACT_CHECK, "Consolidado"),
        (ft.Icons.INSIGHTS_OUTLINED, ft.Icons.INSIGHTS, "Análisis"),
        (ft.Icons.DESCRIPTION_OUTLINED, ft.Icons.DESCRIPTION, "Informes"),
    ]

    def alternar_menu(_e) -> None:
        """Expande (íconos + nombres) o contrae (solo íconos) el menú lateral."""
        rail.extended = not rail.extended
        btn_menu.icon = ft.Icons.MENU_OPEN if rail.extended else ft.Icons.MENU
        btn_menu.tooltip = "Contraer menú" if rail.extended else "Expandir menú"
        rail.update()

    btn_menu = ft.IconButton(ft.Icons.MENU_OPEN, icon_color=tema.TEXTO_SUAVE, tooltip="Contraer menú",
                             on_click=alternar_menu)
    rail = ft.NavigationRail(
        selected_index=0, extended=True, label_type=ft.NavigationRailLabelType.NONE,
        min_width=80, min_extended_width=210,
        bgcolor=tema.SUPERFICIE, indicator_color=tema.PRIMARIO_SUAVE, on_change=cambiar,
        # Color explícito: sin él, las etiquetas heredan el del tema y en algunos equipos no se ven.
        selected_label_text_style=ft.TextStyle(size=15, weight=ft.FontWeight.W_600, color=tema.PRIMARIO),
        unselected_label_text_style=ft.TextStyle(size=15, color=tema.TEXTO),
        leading=ft.Container(
            ft.Column([btn_menu,
                       ft.Icon(ft.Icons.SCHOOL_ROUNDED, size=34, color=tema.PRIMARIO),
                       ft.Text("Notas", size=17, weight=ft.FontWeight.W_700, color=tema.TEXTO)],
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            padding=ft.Padding.only(top=10, bottom=18)),
        destinations=[
            # El tooltip muestra el nombre cuando el menú está contraído.
            ft.NavigationRailDestination(icon=icono, selected_icon=icono_sel, label=nombre, tooltip=nombre)
            for icono, icono_sel, nombre in secciones
        ])

    page.add(ft.Row([rail, ft.VerticalDivider(width=1, color=tema.BORDE), contenido],
                    expand=True, spacing=0))
