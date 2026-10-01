"""Presentación - gráficos hechos con controles de Flet (sin dependencias extra).

* :func:`barra_apilada`: barra al 100 % dividida por estado.
* :func:`fila_barra`: barra apilada con su rótulo y su ``n``.
* :func:`leyenda`: referencias de color de los estados.
* :func:`histograma`: columnas por nota (1 a 10) con la línea de aprobación.
* :func:`matriz_transiciones`: estado del 1.er cuatrimestre contra el del 2.º.
* :func:`barras_riesgo`: alumnos según cuántas materias tienen con CF < 7.

Los colores salen de :data:`app.ui.tema.COLOR_GRAFICO`; cada segmento lleva
además su % escrito (si entra) y un tooltip, para no depender solo del color.
"""
from __future__ import annotations

import flet as ft

from app.config import NOTA_APROBACION, NOTA_MIN, ZONA_LIMITE_DESDE
from app.logic.analisis import ESTADOS_CUATRIMESTRE, Histograma, Riesgo, Transiciones
from app.logic.calificaciones import Estado
from app.logic.estadisticas import Resumen
from app.ui import tema

# (estado, atributo de Resumen) en el orden en que se apilan
ORDEN = [(Estado.APROBADO, "aprobados"), (Estado.DESAPROBADO, "desaprobados"),
         (Estado.AUSENTE, "ausentes"), (Estado.PENDIENTE, "pendientes")]
# % mínimo de un segmento para escribirle el número adentro (depende del ancho de la barra)
PCT_MIN_ROTULO = 5.0


def fmt_pct(valor: float) -> str:
    """42.66 -> '42,7 %'."""
    return f"{valor:.1f}".replace(".", ",") + " %"


def fmt_num(valor: int) -> str:
    """11220 -> '11.220'."""
    return f"{valor:,}".replace(",", ".")


def barra_apilada(r: Resumen, alto: int = 24, pct_min_rotulo: float = PCT_MIN_ROTULO) -> ft.Control:
    if not r.total:
        return ft.Container(ft.Text("Sin datos", size=11.5, color=tema.TEXTO_SUAVE), height=alto,
                            bgcolor=tema.FILA_ALTERNA, border_radius=4, alignment=ft.Alignment.CENTER)
    segmentos = []
    for estado, attr in ORDEN:
        cantidad = getattr(r, attr)
        if not cantidad:
            continue
        pct = r.porcentaje(cantidad)
        relleno, texto = tema.COLOR_GRAFICO[estado]
        segmentos.append(ft.Container(
            ft.Text(fmt_pct(pct), size=11.5, weight=ft.FontWeight.W_600, color=texto, no_wrap=True)
            if pct >= pct_min_rotulo else None,
            expand=cantidad, height=alto, bgcolor=relleno, alignment=ft.Alignment.CENTER,
            tooltip=f"{estado.value}: {fmt_num(cantidad)} de {fmt_num(r.total)} ({fmt_pct(pct)})"))
    # spacing=2 deja un hueco del color de fondo entre segmentos; el recorte redondea los extremos.
    return ft.Container(ft.Row(segmentos, spacing=2), border_radius=4,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS)


def fila_barra(rotulo: str, r: Resumen, ancho_rotulo: int = 170, alto: int = 24,
               pct_min_rotulo: float = PCT_MIN_ROTULO) -> ft.Control:
    return ft.Row([
        ft.Container(ft.Text(rotulo, size=13, color=tema.TEXTO, no_wrap=True,
                             overflow=ft.TextOverflow.ELLIPSIS, tooltip=rotulo), width=ancho_rotulo),
        ft.Container(barra_apilada(r, alto, pct_min_rotulo), expand=True),
        ft.Container(ft.Text(f"n = {fmt_num(r.total)}", size=12, color=tema.TEXTO_SUAVE),
                     width=72, alignment=ft.Alignment.CENTER_RIGHT),
    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def leyenda() -> ft.Control:
    def item(estado: Estado) -> ft.Control:
        return ft.Row([ft.Container(width=12, height=12, border_radius=3, bgcolor=tema.COLOR_GRAFICO[estado][0]),
                       ft.Text(estado.value, size=12.5, color=tema.TEXTO_SUAVE)], spacing=6, tight=True)
    return ft.Row([item(e) for e, _ in ORDEN], spacing=18, wrap=True)


def histograma(h: Histograma, alto: int = 170) -> ft.Control:
    """Una columna por nota; antes del 7 en naranja y desde el 7 en verde.

    La zona límite se marca con una franja de fondo y un rótulo (no con otro color).
    """
    maximo = max(h.conteos) or 1
    desap, _ = tema.COLOR_GRAFICO[Estado.DESAPROBADO]
    aprob, _ = tema.COLOR_GRAFICO[Estado.APROBADO]
    columnas: list[ft.Control] = []
    for i, cantidad in enumerate(h.conteos):
        nota = i + NOTA_MIN
        if nota == NOTA_APROBACION:          # línea de aprobación entre el 6 y el 7
            columnas.append(ft.Column([
                ft.Text("aprueba", size=10.5, color=tema.TEXTO_SUAVE),
                ft.Container(width=2, height=alto + 4, bgcolor=tema.TEXTO_SUAVE, border_radius=1),
                ft.Text("", size=12)], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        rango = f"{nota} a {nota},99" if nota < 10 else "10"
        alto_barra = round(alto * cantidad / maximo)
        barra = ft.Container(
            width=30, height=max(alto_barra, 2 if cantidad else 0),
            bgcolor=aprob if nota >= NOTA_APROBACION else desap,
            border_radius=ft.BorderRadius.only(top_left=4, top_right=4))
        zona = ZONA_LIMITE_DESDE <= nota < NOTA_APROBACION
        columnas.append(ft.Container(
            ft.Column([
                ft.Text("zona límite" if zona else "", size=10.5, color=tema.TEXTO_SUAVE, no_wrap=True),
                ft.Text(fmt_num(cantidad) if cantidad else "", size=11.5, color=tema.TEXTO),
                ft.Container(barra, height=alto, alignment=ft.Alignment.BOTTOM_CENTER),
                ft.Text(str(nota), size=12, color=tema.TEXTO_SUAVE),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True, bgcolor=tema.FONDO_ZONA_LIMITE if zona else None, border_radius=6,
            padding=ft.Padding.symmetric(vertical=4),
            tooltip=f"Nota {rango}: {fmt_num(cantidad)}"))
    return ft.Row(columnas, spacing=4, vertical_alignment=ft.CrossAxisAlignment.END)


def _mezclar(color: str, t: float) -> str:
    """Mezcla ``color`` con blanco: t = 0 -> blanco, t = 1 -> ``color`` (escala secuencial de un tono)."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(255 + (c - 255) * t):02X}" for c in (r, g, b))


def matriz_transiciones(t: Transiciones, ancho_celda: int = 104, alto_celda: int = 50) -> ft.Control:
    """Filas = estado en el 1.er cuatrimestre; columnas = estado en el 2.º.

    El color de cada celda es el % de su fila (un solo tono, más oscuro = más alumnos).
    """
    def encabezado(estado: Estado) -> ft.Control:
        return ft.Row([ft.Container(width=10, height=10, border_radius=2, bgcolor=tema.COLOR_GRAFICO[estado][0]),
                       ft.Text(estado.value, size=12, color=tema.TEXTO_SUAVE, no_wrap=True)],
                      spacing=5, tight=True)

    ancho_rotulo = 132
    filas: list[ft.Control] = [ft.Row(
        [ft.Container(ft.Text("1.er C. ↓   2.º C. →", size=11.5, color=tema.TEXTO_SUAVE), width=ancho_rotulo)]
        + [ft.Container(encabezado(e), width=ancho_celda, alignment=ft.Alignment.CENTER) for e in ESTADOS_CUATRIMESTRE],
        spacing=4)]
    for e1 in ESTADOS_CUATRIMESTRE:
        celdas: list[ft.Control] = [ft.Container(
            ft.Column([encabezado(e1),
                       ft.Text(f"n = {fmt_num(t.total_fila(e1))}", size=11, color=tema.TEXTO_SUAVE)], spacing=0),
            width=ancho_rotulo)]
        for e2 in ESTADOS_CUATRIMESTRE:
            cantidad, pct = t.cantidad(e1, e2), t.pct_fila(e1, e2)
            intensidad = pct / 100
            texto = "#FFFFFF" if intensidad >= 0.65 else tema.TEXTO
            celdas.append(ft.Container(
                ft.Column([ft.Text(fmt_pct(pct), size=13, weight=ft.FontWeight.W_600, color=texto),
                           ft.Text(fmt_num(cantidad), size=11, color=texto)],
                          spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          alignment=ft.MainAxisAlignment.CENTER) if cantidad else None,
                width=ancho_celda, height=alto_celda, border_radius=6, alignment=ft.Alignment.CENTER,
                bgcolor=_mezclar(tema.PRIMARIO, max(intensidad, 0.04)),
                tooltip=(f"{e1.value} en el 1.er C. → {e2.value} en el 2.º C.: {fmt_num(cantidad)} "
                         f"({fmt_pct(pct)} de los {fmt_num(t.total_fila(e1))} {e1.value.lower()}s del 1.er C.)")))
        filas.append(ft.Row(celdas, spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER))
    return ft.Column(filas, spacing=4)


def barras_riesgo(r: Riesgo, alto: int = 22) -> ft.Control:
    """Una barra por cantidad de materias con CF < 7; la última ("N o más") resalta a los alumnos en riesgo."""
    maximo = max(r.por_cantidad) or 1
    ultimo = len(r.por_cantidad) - 1
    filas = []
    for k, cantidad in enumerate(r.por_cantidad):
        en_riesgo = k == ultimo
        rotulo = f"{k} o más" if en_riesgo else str(k)
        rotulo += " materia" if k == 1 and not en_riesgo else " materias"
        pct = 100 * cantidad / r.total_alumnos if r.total_alumnos else 0
        color = tema.COLOR_GRAFICO[Estado.DESAPROBADO][0] if en_riesgo else tema.PRIMARIO
        filas.append(ft.Row([
            ft.Container(ft.Text(rotulo, size=13, color=tema.TEXTO,
                                 weight=ft.FontWeight.W_600 if en_riesgo else None), width=120),
            ft.Container(ft.Row([
                ft.Container(expand=cantidad, height=alto, bgcolor=color, border_radius=4) if cantidad else
                ft.Container(width=0),
                ft.Container(expand=maximo - cantidad) if maximo > cantidad else ft.Container(width=0),
            ], spacing=0), expand=True,
                tooltip=f"{rotulo}: {fmt_num(cantidad)} alumnos ({fmt_pct(pct)})"),
            ft.Container(ft.Text(f"{fmt_num(cantidad)}  ·  {fmt_pct(pct)}", size=12, color=tema.TEXTO_SUAVE),
                         width=110, alignment=ft.Alignment.CENTER_RIGHT),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER))
    return ft.Column(filas, spacing=8)
