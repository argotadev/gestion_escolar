"""Vista - Alta, edición y baja de estudiantes por curso (Flet)."""
from __future__ import annotations

import re
from typing import Optional

import flet as ft

from app.data import repository as repo
from app.ui import tema
from app.ui.comun import etiqueta_curso

_RE_DNI = re.compile(r"^\d{7,8}$")

W_IDX, W_APE, W_NOM, W_DNI, W_ACC = 40, 260, 260, 140, 100


def _normalizar(texto: str) -> str:
    """Quita espacios sobrantes y acentos sueltos: '  jos´é   pérez ' -> 'josé pérez'."""
    return " ".join(tema.limpiar_acentos(texto).split())


class VistaEstudiantes:
    """Listado de estudiantes de un curso con formulario de carga."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.cursos = repo.listar_cursos()
        self._cursos = {str(c.id): c for c in self.cursos}
        self._editando: Optional[repo.Alumno] = None

        self.dd_curso = tema.desplegable(
            "Curso", [(str(c.id), etiqueta_curso(c)) for c in self.cursos],
            str(self.cursos[0].id), 300, lambda _e: self._al_elegir_curso())
        self.lbl_info = ft.Text("", size=15, color=tema.TEXTO_SUAVE)

        # ---- formulario
        self.lbl_form = ft.Text("Nuevo estudiante", size=17, weight=ft.FontWeight.W_700,
                                color=tema.TEXTO)
        self.tf_apellido = tema.campo_texto("Apellido", ancho=240, capitalization=ft.TextCapitalization.WORDS)
        self.tf_nombre = tema.campo_texto("Nombre", ancho=240, capitalization=ft.TextCapitalization.WORDS)
        self.tf_dni = tema.campo_texto("DNI", ancho=150, max_length=8,
                                       input_filter=ft.NumbersOnlyInputFilter(),
                                       on_submit=lambda _e: self.guardar())
        self.dd_curso_form = tema.desplegable(
            "Curso", [(str(c.id), etiqueta_curso(c)) for c in self.cursos],
            self.dd_curso.value, 300, None)
        self.btn_guardar = tema.boton_primario("Agregar", ft.Icons.PERSON_ADD_ALT_1, lambda _e: self.guardar())
        self.btn_cancelar = tema.boton_secundario("Cancelar", ft.Icons.CLOSE, lambda _e: self._limpiar_form())
        self.btn_cancelar.visible = False

        formulario = ft.Column([
            self.lbl_form,
            ft.Row([self.tf_apellido, self.tf_nombre, self.tf_dni, self.dd_curso_form,
                    self.btn_guardar, self.btn_cancelar],
                   spacing=12, wrap=True, vertical_alignment=ft.CrossAxisAlignment.START),
        ], spacing=10)

        self.lista = ft.ListView(expand=True, spacing=0)
        cuerpo = ft.Column([self._encabezado(), ft.Divider(height=1, color=tema.BORDE), self.lista],
                           spacing=0, expand=True)

        self.control = ft.Column([
            tema.titulo_pagina("Estudiantes",
                               "Cargue la lista de estudiantes de cada curso. "
                               "Cada estudiante aparece automáticamente en todas las materias de su curso."),
            tema.tarjeta(formulario, padding=14),
            tema.tarjeta(ft.Row([self.dd_curso, ft.Container(expand=True), self.lbl_info],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=14),
            tema.tarjeta(cuerpo, padding=ft.Padding.only(left=8, right=8, top=8, bottom=4), expand=True),
        ], spacing=16, expand=True)

        self._cargar_lista()

    # ------------------------------------------------------------ componentes
    @staticmethod
    def _celda(texto: str, ancho: int, **kw) -> ft.Container:
        return ft.Container(ft.Text(texto, size=15, no_wrap=True, **kw), width=ancho,
                            padding=ft.Padding.symmetric(horizontal=6))

    def _encabezado(self) -> ft.Control:
        def th(t, w):
            return self._celda(t, w, weight=ft.FontWeight.W_700, color=tema.TEXTO_SUAVE)
        return ft.Container(
            ft.Row([th("#", W_IDX), th("Apellido", W_APE), th("Nombre", W_NOM),
                    th("DNI", W_DNI), th("Acciones", W_ACC)], spacing=0),
            padding=ft.Padding.symmetric(vertical=10, horizontal=8), bgcolor=tema.FILA_ALTERNA)

    def _fila(self, i: int, a: repo.Alumno) -> ft.Control:
        acciones = ft.Row([
            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=18, tooltip="Editar",
                          icon_color=tema.PRIMARIO, on_click=lambda _e, a=a: self._editar(a)),
            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, tooltip="Eliminar",
                          icon_color="#C0392B", on_click=lambda _e, a=a: self._confirmar_baja(a)),
        ], spacing=0, width=W_ACC)
        return ft.Container(
            ft.Row([self._celda(str(i), W_IDX, color=tema.TEXTO_SUAVE),
                    self._celda(a.apellido, W_APE), self._celda(a.nombre, W_NOM),
                    self._celda(a.dni, W_DNI), acciones],
                   spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(vertical=2, horizontal=8),
            bgcolor=tema.FILA_ALTERNA if i % 2 == 0 else tema.SUPERFICIE)

    # ------------------------------------------------------------------ datos
    def al_mostrar(self) -> None:
        self._cargar_lista()
        self._actualizar(self.lista, self.lbl_info)

    def _al_elegir_curso(self) -> None:
        if self._editando is None:
            self.dd_curso_form.value = self.dd_curso.value
        self._cargar_lista()
        self._actualizar(self.lista, self.lbl_info, self.dd_curso_form)

    def _cargar_lista(self) -> None:
        alumnos = repo.listar_alumnos(int(self.dd_curso.value))
        self.lista.controls = [self._fila(i, a) for i, a in enumerate(alumnos, 1)] or [
            ft.Container(ft.Text("Este curso todavía no tiene estudiantes cargados.",
                                 color=tema.TEXTO_SUAVE), padding=20)]
        self.lbl_info.value = f"{len(alumnos)} estudiante(s)"

    def _actualizar(self, *controles: ft.Control) -> None:
        """Actualiza controles solo si la vista ya está montada en la página."""
        for c in controles:
            try:
                c.update()
            except RuntimeError:
                pass

    # ------------------------------------------------------------- formulario
    def _validar(self) -> Optional[tuple[str, str, str, int]]:
        apellido, nombre = _normalizar(self.tf_apellido.value), _normalizar(self.tf_nombre.value)
        dni = (self.tf_dni.value or "").strip()
        errores = {self.tf_apellido: None if apellido else "Obligatorio",
                   self.tf_nombre: None if nombre else "Obligatorio",
                   self.tf_dni: None if _RE_DNI.match(dni) else "7 u 8 dígitos"}
        for tf, err in errores.items():
            tf.error = err
        self._actualizar(*errores)
        if any(errores.values()):
            return None
        return apellido, nombre, dni, int(self.dd_curso_form.value)

    def guardar(self) -> None:
        datos = self._validar()
        if datos is None:
            return
        try:
            if self._editando is None:
                repo.crear_alumno(*datos)
                mensaje = f"Se agregó a {datos[0]}, {datos[1]}."
            else:
                repo.actualizar_alumno(self._editando.id, *datos)
                mensaje = "Datos del estudiante actualizados."
        except repo.DniDuplicado:
            self.tf_dni.error = "Ya existe un estudiante con ese DNI"
            self._actualizar(self.tf_dni)
            return
        curso_form = self.dd_curso_form.value
        self._limpiar_form()
        if curso_form != self.dd_curso.value:      # mostrar el curso donde quedó el alumno
            self.dd_curso.value = self.dd_curso_form.value = curso_form
        self._cargar_lista()
        self._actualizar(self.dd_curso, self.dd_curso_form, self.lista, self.lbl_info)
        tema.avisar(self.page, mensaje)
        self.tf_apellido.focus()

    def _editar(self, a: repo.Alumno) -> None:
        self._editando = a
        self.tf_apellido.value, self.tf_nombre.value, self.tf_dni.value = a.apellido, a.nombre, a.dni
        self.dd_curso_form.value = str(a.curso_id)
        self.lbl_form.value = f"Editando: {a.nombre_completo}"
        self.btn_guardar.content, self.btn_guardar.icon = "Guardar", ft.Icons.SAVE_OUTLINED
        self.btn_cancelar.visible = True
        self._refrescar_form()

    def _limpiar_form(self) -> None:
        self._editando = None
        for tf in (self.tf_apellido, self.tf_nombre, self.tf_dni):
            tf.value, tf.error = "", None
        self.dd_curso_form.value = self.dd_curso.value
        self.lbl_form.value = "Nuevo estudiante"
        self.btn_guardar.content, self.btn_guardar.icon = "Agregar", ft.Icons.PERSON_ADD_ALT_1
        self.btn_cancelar.visible = False
        self._refrescar_form()

    def _refrescar_form(self) -> None:
        self._actualizar(self.lbl_form, self.tf_apellido, self.tf_nombre, self.tf_dni,
                         self.dd_curso_form, self.btn_guardar, self.btn_cancelar)

    # ------------------------------------------------------------------- baja
    def _confirmar_baja(self, a: repo.Alumno) -> None:
        n = repo.contar_notas_alumno(a.id)
        detalle = (f"\n\nAtención: tiene notas cargadas en {n} materia(s), que también se borrarán."
                   if n else "")

        def eliminar(_e):
            self.page.pop_dialog()
            repo.eliminar_alumno(a.id)
            if self._editando and self._editando.id == a.id:
                self._limpiar_form()
            self._cargar_lista()
            self._actualizar(self.lista, self.lbl_info)
            tema.avisar(self.page, f"Se eliminó a {a.nombre_completo}.")

        self.page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text("Eliminar estudiante"),
            content=ft.Text(f"¿Eliminar a {a.nombre_completo} (DNI {a.dni})?{detalle}"),
            actions=[ft.TextButton("Cancelar", on_click=lambda _e: self.page.pop_dialog()),
                     ft.FilledButton("Eliminar", on_click=eliminar,
                                     style=ft.ButtonStyle(bgcolor="#C0392B", color="#FFFFFF"))]))
