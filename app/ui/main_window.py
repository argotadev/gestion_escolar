"""Ventana principal (Flet): barra de navegación lateral + vistas."""
from __future__ import annotations

import flet as ft

from app.config import DB_PATH
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

    vista_carga, vista_informes = VistaCarga(page), VistaInformes(page)
    vistas = [VistaEstudiantes(page), vista_carga, VistaConsolidado(page), VistaAnalisis(page),
              vista_informes]
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

    # ---- Cierre: no perder cambios sin avisar --------------------------------
    async def salir(_e=None) -> None:
        await page.window.destroy()

    async def guardar_y_salir(_e) -> None:
        page.pop_dialog()
        if vista_carga.guardar():           # si falla, ya mostró el error y la ventana sigue abierta
            await salir()

    async def al_evento_ventana(e: ft.WindowEvent) -> None:
        if e.type != ft.WindowEventType.CLOSE:
            return
        pendientes = []
        if vista_carga.hay_cambios:
            pendientes.append("• Notas modificadas en «Carga de notas» que todavía no se guardaron.")
        try:
            vista_informes.guardar_borrador()
        except Exception as exc:            # noqa: BLE001 - se informa en el diálogo
            pendientes.append(f"• Los textos del informe (no se pudieron guardar: {exc}).")
        if not pendientes:
            await salir()
            return
        acciones = [ft.TextButton("Cancelar", on_click=lambda _e: page.pop_dialog()),
                    ft.TextButton("Salir sin guardar", on_click=salir)]
        if vista_carga.hay_cambios:
            acciones.append(ft.FilledButton("Guardar notas y salir", on_click=guardar_y_salir))
        page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text("Hay cambios sin guardar"),
            content=ft.Text("Si sale ahora se pierde:\n" + "\n".join(pendientes), size=15),
            actions=acciones))

    page.window.prevent_close = True
    page.window.on_event = al_evento_ventana
    page.update()


def error_inicio(page: ft.Page, detalle: str) -> None:
    """Pantalla en lugar de la aplicación si la base de datos no se puede crear o no admite escritura."""
    page.title = TITULO
    page.theme = tema.crear_tema()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = tema.FONDO
    page.window.width, page.window.height = 780, 480

    async def cerrar(_e) -> None:
        await page.window.destroy()

    page.add(ft.Container(tema.tarjeta(ft.Column([
        ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color="#B3261E", size=32),
                ft.Text("No se puede guardar la base de datos", size=22, weight=ft.FontWeight.W_700,
                        color=tema.TEXTO)], spacing=12),
        ft.Text("El programa no puede escribir en la base de datos, así que nada de lo que se cargue "
                "quedaría guardado. Verifique que la carpeta tenga permisos de escritura (no use "
                "«Archivos de programa» ni una carpeta de solo lectura) y que el antivirus o el "
                "«Acceso controlado a carpetas» de Windows no bloqueen el programa.", size=15, color=tema.TEXTO),
        ft.Text(f"Base de datos: {DB_PATH}", size=14, color=tema.TEXTO_SUAVE, selectable=True),
        ft.Text(f"Detalle: {detalle}", size=14, color=tema.TEXTO_SUAVE, selectable=True),
        ft.Row([ft.FilledButton("Cerrar", on_click=cerrar)], alignment=ft.MainAxisAlignment.END),
    ], spacing=14, tight=True), padding=24), padding=24, alignment=ft.Alignment.CENTER, expand=True))
