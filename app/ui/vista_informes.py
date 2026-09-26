"""Vista 3 - Generación del informe departamental (Word) - Flet."""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import flet as ft

from app.config import OUTPUT_DIR
from app.data import repository as repo
from app.reports.informe_docx import CAMPOS_CUALITATIVOS, DatosInforme, generar_informe
from app.ui import tema
from app.ui.comun import abrir_archivo

PERIODOS = ["PRIMER CUATRIMESTRE", "SEGUNDO CUATRIMESTRE", "ANUAL"]


class VistaInformes:
    def __init__(self, page: ft.Page):
        self.page = page
        self.departamentos = repo.listar_departamentos()
        self._por_id = {str(d.id): d for d in self.departamentos}
        self._dep_actual = str(self.departamentos[0].id)
        self.cajas: dict[str, ft.TextField] = {}

        self.dd_dep = tema.desplegable(
            "Departamento", [(str(d.id), d.nombre) for d in self.departamentos],
            self._dep_actual, 470, self._al_elegir_departamento)
        self.tf_jefe = tema.campo_texto("Jefe/a de departamento", ancho=470)
        self.tf_anio = tema.campo_texto("Ciclo lectivo", str(dt.date.today().year), 130,
                                        max_length=4, counter=ft.Text(""),
                                        input_filter=ft.NumbersOnlyInputFilter())
        self.dd_periodo = tema.desplegable("Período", [(p, p) for p in PERIODOS], "ANUAL", 260, lambda _e: None)

        general = tema.tarjeta(ft.Column([
            ft.Text("Datos generales", size=15, weight=ft.FontWeight.W_600, color=tema.TEXTO),
            ft.Row([self.dd_dep, self.tf_anio, self.dd_periodo], spacing=14, wrap=True),
            ft.Row([self.tf_jefe]),
        ], spacing=12), padding=18)

        campos: list[ft.Control] = [
            ft.Text("Informe cualitativo", size=15, weight=ft.FontWeight.W_600, color=tema.TEXTO),
            ft.Text("Cada texto se agrega a continuación de su rótulo en la plantilla. "
                    "Los campos vacíos se dejan sin completar.", size=12.5, color=tema.TEXTO_SUAVE),
        ]
        for clave, rotulo in CAMPOS_CUALITATIVOS:
            caja = tema.campo_texto(rotulo.rstrip(":"), multiline=True, min_lines=3, max_lines=8)
            caja.on_change = None
            self.cajas[clave] = caja
            campos.append(caja)
        cualitativo = tema.tarjeta(ft.Column(campos, spacing=14, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                                   padding=18)

        self.btn_generar = tema.boton_primario("Generar informe (.docx)", ft.Icons.DESCRIPTION_OUTLINED,
                                               self.generar)
        pie = ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=tema.TEXTO_SUAVE),
            ft.Text("Los datos cuantitativos (total, aprobados, desaprobados y ausentes por curso y división) "
                    "se calculan desde la base de datos.", size=12.5, color=tema.TEXTO_SUAVE, expand=True),
            self.btn_generar], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        self.control = ft.Column([
            tema.titulo_pagina("Informe de Departamento",
                               "Genera el informe en Word a partir de la plantilla oficial."),
            ft.Column([general, cualitativo], scroll=ft.ScrollMode.AUTO, expand=True, spacing=16,
                      horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            tema.tarjeta(pie, padding=ft.Padding.symmetric(horizontal=16, vertical=10)),
        ], spacing=16, expand=True)
        self._cargar_departamento()

    def _actualizar(self, *controles: ft.Control) -> None:
        for c in controles:
            try:
                c.update()
            except RuntimeError:
                pass

    # ------------------------------------------------------------ departamento
    def _cargar_departamento(self) -> None:
        dep = self._por_id[self._dep_actual]
        self.tf_jefe.value = dep.jefe
        textos = repo.cargar_textos_informe(dep.id)
        for clave, caja in self.cajas.items():
            caja.value = textos.get(clave, "")

    def _guardar_borrador(self) -> None:
        """Guarda jefe y textos del departamento actual para no perderlos al cambiar."""
        dep = self._por_id[self._dep_actual]
        repo.actualizar_jefe(dep.id, self.tf_jefe.value.strip())
        repo.guardar_textos_informe(dep.id, {k: (c.value or "").strip() for k, c in self.cajas.items()})

    def _al_elegir_departamento(self, _e) -> None:
        nuevo = self.dd_dep.value
        if nuevo == self._dep_actual:
            return
        self._guardar_borrador()
        self._refrescar_departamentos()
        self._dep_actual = nuevo
        self._cargar_departamento()
        self._actualizar(self.tf_jefe, *self.cajas.values())

    def _refrescar_departamentos(self) -> None:
        self.departamentos = repo.listar_departamentos()
        self._por_id = {str(d.id): d for d in self.departamentos}

    def al_mostrar(self) -> None:
        pass

    # --------------------------------------------------------------- generar
    def generar(self, _e=None) -> None:
        anio = (self.tf_anio.value or "").strip()
        if not re.fullmatch(r"\d{4}", anio):
            tema.avisar(self.page, "El ciclo lectivo debe ser un año de 4 dígitos.", error=True)
            return
        dep = self._por_id[self._dep_actual]
        try:
            self._guardar_borrador()
            self._refrescar_departamentos()
            dep = self._por_id[self._dep_actual]
            textos = {k: (c.value or "").strip() for k, c in self.cajas.items()}
            datos = DatosInforme(dep, anio, self.dd_periodo.value, textos)
            base = re.sub(r"[^\w]+", "_", dep.nombre).strip("_")
            periodo = re.sub(r"[^\w]+", "_", self.dd_periodo.value).strip("_")
            ruta = OUTPUT_DIR / f"Informe_{base}_{anio}_{periodo}.docx"
            try:
                salida = generar_informe(datos, ruta)
            except PermissionError:      # el archivo está abierto en Word: se guarda con otro nombre
                ruta = ruta.with_name(f"{ruta.stem}_{dt.datetime.now():%H%M%S}.docx")
                salida = generar_informe(datos, ruta)
        except Exception as exc:                      # noqa: BLE001 - se informa al usuario
            tema.avisar(self.page, f"No se pudo generar el informe: {exc}", error=True)
            return
        self._dialogo_listo(Path(salida))

    def _dialogo_listo(self, salida: Path) -> None:
        def cerrar(_e=None):
            self.page.pop_dialog()

        def abrir(_e):
            cerrar()
            abrir_archivo(salida)

        def abrir_carpeta(_e):
            cerrar()
            abrir_archivo(salida.parent)

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color="#1B7F3B"), ft.Text("Informe generado")], spacing=10),
            content=ft.Column([ft.Text("Se guardó en:", size=13, color=tema.TEXTO_SUAVE),
                               ft.Text(str(salida), size=13, selectable=True)], tight=True, spacing=4),
            actions=[ft.TextButton("Cerrar", on_click=cerrar),
                     ft.TextButton("Abrir carpeta", on_click=abrir_carpeta),
                     ft.FilledButton("Abrir informe", on_click=abrir)]))
