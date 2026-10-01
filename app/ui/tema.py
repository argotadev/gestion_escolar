"""Presentación - paleta, tema y componentes visuales reutilizables (Flet)."""
from __future__ import annotations

import re
from typing import Callable, Optional

import flet as ft

from app.logic.calificaciones import Estado

# ---- Paleta -----------------------------------------------------------------
PRIMARIO = "#3949AB"
PRIMARIO_SUAVE = "#E8EAF6"
FONDO = "#F4F6FB"
SUPERFICIE = "#FFFFFF"
BORDE = "#E3E7EF"
TEXTO = "#1F2937"
TEXTO_SUAVE = "#6B7280"
FILA_ALTERNA = "#F9FAFD"

# Estado -> (color del texto, color de fondo de la "pastilla")
COLOR_ESTADO: dict[Estado, tuple[str, str]] = {
    Estado.APROBADO: ("#1B7F3B", "#E6F4EA"),
    Estado.DESAPROBADO: ("#C0392B", "#FDECEA"),
    Estado.AUSENTE: ("#5B4B8A", "#EFEBF8"),
    Estado.PENDIENTE: ("#6B7280", "#EEF0F4"),
}
COLOR_VA_A_IFA = ("#B26A00", "#FFF4E0")   # CF < 7: debe rendir la IFA


def crear_tema() -> ft.Theme:
    return ft.Theme(color_scheme_seed=PRIMARIO, use_material3=True)


# ---- Componentes ------------------------------------------------------------
def tarjeta(contenido: ft.Control, padding: int | ft.Padding = 16, **kw) -> ft.Container:
    """Panel blanco con borde suave y sombra ligera."""
    return ft.Container(
        content=contenido, bgcolor=SUPERFICIE, border_radius=14, padding=padding,
        border=ft.Border.all(1, BORDE),
        shadow=ft.BoxShadow(blur_radius=14, color=ft.Colors.with_opacity(0.06, "#0F172A"),
                            offset=ft.Offset(0, 3)),
        **kw)


def titulo_pagina(titulo: str, subtitulo: str = "") -> ft.Control:
    partes: list[ft.Control] = [ft.Text(titulo, size=26, weight=ft.FontWeight.W_700, color=TEXTO)]
    if subtitulo:
        partes.append(ft.Text(subtitulo, size=13.5, color=TEXTO_SUAVE))
    return ft.Column(partes, spacing=2)


def pastilla_estado(estado: Estado, ancho: Optional[int] = None) -> ft.Container:
    """Etiqueta redondeada con el color del estado."""
    return pastilla(estado.value, *COLOR_ESTADO[estado], ancho=ancho)


def pastilla(texto: str, color: str, fondo: str, ancho: Optional[int] = None) -> ft.Container:
    """Etiqueta redondeada genérica."""
    return ft.Container(
        content=ft.Text(texto, size=12, weight=ft.FontWeight.W_600, color=color,
                        no_wrap=True),
        bgcolor=fondo, border_radius=20, width=ancho, alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4))


def desplegable(etiqueta: str, opciones: list[tuple[str, str]], valor: str, ancho: int,
                al_elegir: Callable) -> ft.Dropdown:
    """Dropdown con estilo uniforme. ``opciones`` = [(clave, texto), ...]."""
    return ft.Dropdown(
        label=etiqueta, value=valor, width=ancho, dense=True, text_size=13.5,
        options=[ft.DropdownOption(key=k, text=t) for k, t in opciones],
        border_radius=10, border_color=BORDE, filled=True, fill_color=SUPERFICIE,
        on_select=al_elegir)


# Flutter en Linux deja suelto el acento de las teclas muertas: "´" + "e" -> "´é".
_RE_ACENTO_SUELTO = re.compile(r"[´¨`^~](?=[^\W\d_])")


def limpiar_acentos(texto: str) -> str:
    """Quita el acento suelto que precede a una letra: 'Jos´é' -> 'José'."""
    return _RE_ACENTO_SUELTO.sub("", texto or "")


def campo_texto(etiqueta: str, valor: str = "", ancho: Optional[int] = None, **kw) -> ft.TextField:
    al_cambiar = kw.pop("on_change", None)

    def on_change(e) -> None:
        limpio = limpiar_acentos(e.control.value)
        if limpio != e.control.value:
            e.control.value = limpio
            e.control.update()
        if al_cambiar:
            al_cambiar(e)

    return ft.TextField(
        label=etiqueta, value=valor, width=ancho, dense=True, text_size=13.5,
        border_radius=10, border_color=BORDE, filled=True, fill_color=SUPERFICIE,
        on_change=on_change, **kw)


def boton_primario(texto: str, icono, al_click: Callable) -> ft.FilledButton:
    return ft.FilledButton(
        content=texto, icon=icono, on_click=al_click, height=42,
        style=ft.ButtonStyle(
            bgcolor={ft.ControlState.DISABLED: "#D5D9EC", ft.ControlState.DEFAULT: PRIMARIO},
            color={ft.ControlState.DISABLED: "#9AA1BF", ft.ControlState.DEFAULT: "#FFFFFF"},
            shape=ft.RoundedRectangleBorder(radius=10)))


def boton_secundario(texto: str, icono, al_click: Callable) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        content=texto, icon=icono, on_click=al_click, height=42,
        style=ft.ButtonStyle(
            color={ft.ControlState.DISABLED: "#B0B7C3", ft.ControlState.DEFAULT: PRIMARIO},
            shape=ft.RoundedRectangleBorder(radius=10), side=ft.BorderSide(1, BORDE)))


def avisar(page: ft.Page, mensaje: str, error: bool = False) -> None:
    """Notificación efímera (snackbar) al pie de la ventana."""
    page.show_dialog(ft.SnackBar(
        content=ft.Text(mensaje, color="#FFFFFF"),
        bgcolor="#B3261E" if error else "#2E3A59", duration=3500, behavior=ft.SnackBarBehavior.FLOATING))
