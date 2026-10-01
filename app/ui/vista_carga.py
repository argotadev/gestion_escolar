"""Vista 1 - Carga de notas por curso y materia (C1, C2 e IFA) - Flet."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import flet as ft

from app.config import NOTA_MAX, NOTA_MIN
from app.data import repository as repo
from app.logic.calificaciones import (
    Cuatrimestre,
    RegistroNotas,
    evaluar,
    formatear_cf,
    necesita_intensificacion_cuatrimestral,
)
from app.ui import tema
from app.ui.comun import etiqueta_curso

# (columna en BD, título) en el orden en que se muestran
COL_C1 = [
    ("c1_nota1", "N1"),
    ("c1_nota2", "N2"),
    ("c1_int", "IFC"),
    ("c1_cal", "CC"),
]
COL_C2 = [
    ("c2_nota1", "N1"),
    ("c2_nota2", "N2"),
    ("c2_int", "IFC"),
    ("c2_cal", "CC"),
]
COL_IFA = [("if_nota", "IFA")]
GRUPO_FINAL = "Calif. final"
# En "Calif. final" la grilla muestra CF | Aus. (de la IFA); la columna IFA va
# después del grupo, antes de Estado.
GRUPOS = [
    ("1.er Cuatrimestre", COL_C1, "c1_ausente"),
    ("2.º Cuatrimestre", COL_C2, "c2_ausente"),
    (GRUPO_FINAL, COL_IFA, "if_ausente"),
]
CAMPOS_NOTA = [c for _, cols, _ in GRUPOS for c, _ in cols]
CAMPOS_AUS = [a for _, _, a in GRUPOS]

# Anchos fijos (px) para que cabecera y filas queden perfectamente alineadas.
W_IDX, W_NOM, W_ENT, W_AUS, W_CF, W_EST = 34, 250, 56, 44, 70, 160
W_IFA = len(COL_IFA) * W_ENT
W_GRUPO = {n: (W_CF if n == GRUPO_FINAL else len(cols) * W_ENT) + W_AUS for n, cols, _ in GRUPOS}
GRID_W = W_IDX + W_NOM + sum(W_GRUPO.values()) + W_IFA + W_EST + 16

C_ERROR, C_AVISO = "#E53935", "#FFB300"


@dataclass
class _FilaUI:
    alumno_id: int
    materia_id: int
    campos: dict[str, ft.TextField] = field(default_factory=dict)
    ausentes: dict[str, ft.Checkbox] = field(default_factory=dict)
    tf_cf: Optional[ft.TextField] = None
    pastilla: Optional[ft.Container] = None


def _parsear(texto: str) -> tuple[Optional[int], bool]:
    """'' -> (None, True); entero válido -> (n, True); otro caso -> (None, False)."""
    texto = (texto or "").strip()
    if not texto:
        return None, True
    if texto.isdigit() and NOTA_MIN <= int(texto) <= NOTA_MAX:
        return int(texto), True
    return None, False


_RE_CF = re.compile(r"^(\d{1,2})(?:[.,](\d{0,2}))?$")


def _parsear_cf(texto: str) -> tuple[Optional[float], bool]:
    """Como :func:`_parsear` pero admite hasta 2 decimales ('7,25' o '7.25')."""
    texto = (texto or "").strip()
    if not texto:
        return None, True
    m = _RE_CF.match(texto)
    if not m:
        return None, False
    valor = float(f"{m.group(1)}.{m.group(2) or 0}")
    return (valor, True) if NOTA_MIN <= valor <= NOTA_MAX else (None, False)


def _celda(contenido: ft.Control, ancho: int) -> ft.Container:
    return ft.Container(content=contenido, width=ancho, alignment=ft.Alignment.CENTER)


class VistaCarga:
    """Listado de alumnos de un curso/materia con celdas editables de notas."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.cursos = repo.listar_cursos()
        self._cursos = {str(c.id): c for c in self.cursos}
        self._materias: dict[str, repo.Materia] = {}
        self.filas: list[_FilaUI] = []
        self._cargando = False
        self._sucio = False
        self._curso_prev = str(self.cursos[0].id)
        self._materia_prev = ""

        self.dd_curso = tema.desplegable(
            "Curso",
            [(str(c.id), etiqueta_curso(c)) for c in self.cursos],
            self._curso_prev,
            300,
            self._al_elegir_curso,
        )
        self.dd_materia = tema.desplegable(
            "Materia", [("", "-")], "", 380, self._al_elegir_materia
        )
        self.lbl_info = ft.Text("", size=13, color=tema.TEXTO_SUAVE)
        self.btn_guardar = tema.boton_primario(
            "Guardar cambios", ft.Icons.SAVE_OUTLINED, self.guardar
        )
        self.btn_descartar = tema.boton_secundario(
            "Descartar", ft.Icons.UNDO, self._descartar
        )

        self.lista = ft.ListView(expand=True, spacing=0)
        cuerpo = ft.Container(
            width=GRID_W,
            content=ft.Column(
                [
                    self._encabezado(),
                    ft.Divider(height=1, color=tema.BORDE),
                    self.lista,
                ],
                spacing=0,
                expand=True,
            ),
        )

        leyenda = ft.Row(
            [
                self._punto(C_AVISO, "Falta intensificación (IFC o IFA)"),
                self._punto(C_ERROR, "Nota inválida (1 a 10)"),
                ft.Text(
                    "CC = calificación cuatrimestral (se carga a mano) · IFC = intensificación cuatrimestral · IFA = intensificación anual (solo si CF < 7)",
                    size=12,
                    color=tema.TEXTO_SUAVE,
                ),
                ft.Text(
                    "Aus. = ausente: CC vacía cuenta 4 en la CF",
                    size=12,
                    color=tema.TEXTO_SUAVE,
                ),
            ],
            spacing=22,
            wrap=False,
            scroll=ft.ScrollMode.HIDDEN,
        )

        barra = ft.Row(
            [
                self.dd_curso,
                self.dd_materia,
                ft.Container(expand=True),
                self.lbl_info,
                self.btn_descartar,
                self.btn_guardar,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.control = ft.Column(
            [
                tema.titulo_pagina(
                    "Carga de notas",
                    "Ingrese las notas por curso y materia. "
                    "El estado y la calificación final se calculan al instante.",
                ),
                tema.tarjeta(ft.Column([barra, leyenda], spacing=10), padding=14),
                tema.tarjeta(
                    ft.Row(
                        [cuerpo],
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.Padding.only(left=8, right=8, top=8, bottom=4),
                    expand=True,
                ),
            ],
            spacing=16,
            expand=True,
        )

        self._cargar_materias(self._curso_prev)
        self._cargar_tabla()
        self._actualizar_botones()

    # ------------------------------------------------------------ componentes
    @staticmethod
    def _punto(color: str, texto: str) -> ft.Control:
        return ft.Row(
            [
                ft.Container(width=10, height=10, bgcolor=color, border_radius=5),
                ft.Text(texto, size=12, color=tema.TEXTO_SUAVE),
            ],
            spacing=6,
        )

    def _encabezado(self) -> ft.Control:
        def th(texto, ancho, **kw):
            return _celda(
                ft.Text(
                    texto,
                    size=12,
                    weight=ft.FontWeight.W_700,
                    color=tema.TEXTO_SUAVE,
                    **kw,
                ),
                ancho,
            )

        grupos, sub = (
            [th("", W_IDX), th("", W_NOM)],
            [
                th("#", W_IDX),
                _celda(
                    ft.Text(
                        "Alumno",
                        size=12,
                        weight=ft.FontWeight.W_700,
                        color=tema.TEXTO_SUAVE,
                    ),
                    W_NOM,
                ),
            ],
        )
        for nombre, cols, _ in GRUPOS:
            grupos.append(
                _celda(
                    ft.Text(
                        nombre,
                        size=12.5,
                        weight=ft.FontWeight.W_700,
                        color=tema.PRIMARIO,
                    ),
                    W_GRUPO[nombre],
                )
            )
            if nombre == GRUPO_FINAL:
                sub.append(th("CF", W_CF))
            else:
                sub.extend(th(t, W_ENT) for _, t in cols)
            sub.append(th("Aus.", W_AUS))
        grupos += [th("", W_IFA), th("", W_EST)]
        sub += [th(t, W_ENT) for _, t in COL_IFA] + [th("Estado", W_EST)]
        return ft.Container(
            content=ft.Column(
                [ft.Row(grupos, spacing=0), ft.Row(sub, spacing=0)], spacing=2
            ),
            padding=ft.Padding.symmetric(vertical=8, horizontal=8),
            bgcolor=tema.FILA_ALTERNA,
        )

    def _campo_nota(self, valor: Optional[int], fila: _FilaUI) -> ft.TextField:
        return ft.TextField(
            value="" if valor is None else str(valor),
            width=W_ENT - 8,
            height=38,
            text_size=13.5,
            text_align=ft.TextAlign.CENTER,
            dense=True,
            content_padding=ft.Padding.symmetric(horizontal=2, vertical=9),
            border_radius=8,
            border_color=tema.BORDE,
            focused_border_color=tema.PRIMARIO,
            bgcolor="#FFFFFF",
            filled=True,
            input_filter=ft.NumbersOnlyInputFilter(),
            keyboard_type=ft.KeyboardType.NUMBER,
            hint_style=ft.TextStyle(color="#B0B7C3"),
            on_change=lambda _e, f=fila: self._al_editar(f),
        )

    def _dibujar_fila(self, n: int, f: repo.FilaAlumno) -> ft.Control:
        fila = _FilaUI(f.alumno_id, f.materia_id)
        reg = f.registro
        valores = {
            "c1_nota1": reg.c1.nota1,
            "c1_nota2": reg.c1.nota2,
            "c1_int": reg.c1.intensificacion,
            "c1_cal": reg.c1.calificacion,
            "c2_nota1": reg.c2.nota1,
            "c2_nota2": reg.c2.nota2,
            "c2_int": reg.c2.intensificacion,
            "c2_cal": reg.c2.calificacion,
            "if_nota": reg.if_nota,
        }
        aus = {
            "c1_ausente": reg.c1.ausente,
            "c2_ausente": reg.c2.ausente,
            "if_ausente": reg.if_ausente,
        }

        celdas: list[ft.Control] = [
            _celda(ft.Text(str(n), size=12.5, color=tema.TEXTO_SUAVE), W_IDX),
            ft.Container(
                ft.Text(
                    f.nombre_completo,
                    size=13.5,
                    color=tema.TEXTO,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                width=W_NOM,
                alignment=ft.Alignment.CENTER_LEFT,
            ),
        ]
        fila.tf_cf = self._campo_nota(None, fila)
        fila.tf_cf.value = formatear_cf(reg.cf_manual)
        fila.tf_cf.width = W_CF - 8
        fila.tf_cf.text_style = ft.TextStyle(weight=ft.FontWeight.W_700)
        fila.tf_cf.input_filter = ft.InputFilter(regex_string=r"^\d{0,2}([.,]\d{0,2})?$",
                                                 allow=True, replacement_string="")
        fila.tf_cf.keyboard_type = ft.KeyboardType.TEXT
        fila.tf_cf.tooltip = "Calificación final: vacío = se usa la calculada (en gris). Hasta 2 decimales."

        def campos_nota(cols) -> None:
            for campo, _ in cols:
                tf = self._campo_nota(valores[campo], fila)
                fila.campos[campo] = tf
                celdas.append(_celda(tf, W_ENT))

        for nombre, cols, clave_aus in GRUPOS:
            if nombre == GRUPO_FINAL:
                celdas.append(_celda(fila.tf_cf, W_CF))
            else:
                campos_nota(cols)
            cb = ft.Checkbox(
                value=bool(aus[clave_aus]),
                on_change=lambda _e, fl=fila: self._al_editar(fl),
            )
            fila.ausentes[clave_aus] = cb
            celdas.append(_celda(cb, W_AUS))
        campos_nota(COL_IFA)
        fila.pastilla = ft.Container(width=W_EST, alignment=ft.Alignment.CENTER_LEFT)
        celdas.append(fila.pastilla)
        self.filas.append(fila)
        return ft.Container(
            content=ft.Row(
                celdas, spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            bgcolor=tema.FILA_ALTERNA if n % 2 == 0 else "#FFFFFF",
            padding=ft.Padding.symmetric(vertical=3, horizontal=8),
            border_radius=8,
        )

    # -------------------------------------------------------------- selección
    def _cargar_materias(self, curso_id: str) -> None:
        materias = repo.listar_materias_de_curso(self._cursos[curso_id].id)
        self._materias = {str(m.id): m for m in materias}
        self.dd_materia.options = [
            ft.DropdownOption(key=str(m.id), text=m.nombre) for m in materias
        ]
        self.dd_materia.value = str(materias[0].id)
        self._materia_prev = self.dd_materia.value

    def _actualizar(self, *controles: ft.Control) -> None:
        """Actualiza controles solo si la vista ya está montada en la página."""
        for c in controles:
            try:
                c.update()
            except RuntimeError:
                pass

    def _pedir_confirmacion(self, si_continua, al_cancelar) -> None:
        """Si hay cambios sin guardar pregunta antes de continuar."""
        if not self._sucio:
            si_continua()
            return

        def cerrar(_e=None):
            self.page.pop_dialog()

        def descartar(_e):
            cerrar()
            self._sucio = False
            si_continua()

        def guardar_y_seguir(_e):
            cerrar()
            if self.guardar():
                si_continua()
            else:
                al_cancelar()

        def cancelar(_e):
            cerrar()
            al_cancelar()

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Cambios sin guardar"),
                content=ft.Text("Hay notas modificadas que todavía no se guardaron."),
                actions=[
                    ft.TextButton("Cancelar", on_click=cancelar),
                    ft.TextButton("Descartar", on_click=descartar),
                    ft.FilledButton("Guardar y continuar", on_click=guardar_y_seguir),
                ],
            )
        )

    def _al_elegir_curso(self, _e) -> None:
        nuevo = self.dd_curso.value

        def continuar():
            self._curso_prev = nuevo
            self._cargar_materias(nuevo)
            self._cargar_tabla()
            self._actualizar(self.dd_materia, self.lista, self.lbl_info)
            self._actualizar_botones()

        def volver():
            self.dd_curso.value = self._curso_prev
            self._actualizar(self.dd_curso)

        self._pedir_confirmacion(continuar, volver)

    def _al_elegir_materia(self, _e) -> None:
        nueva = self.dd_materia.value

        def continuar():
            self._materia_prev = nueva
            self._cargar_tabla()
            self._actualizar(self.lista, self.lbl_info)
            self._actualizar_botones()

        def volver():
            self.dd_materia.value = self._materia_prev
            self._actualizar(self.dd_materia)

        self._pedir_confirmacion(continuar, volver)

    def al_mostrar(self) -> None:
        """Hook al entrar en la vista: recarga salvo que haya cambios pendientes."""
        if not self._sucio:
            self._cargar_tabla()
            self._actualizar(self.lista, self.lbl_info)

    def _descartar(self, _e=None) -> None:
        self._sucio = False
        self._cargar_tabla()
        self._actualizar(self.lista, self.lbl_info)
        self._actualizar_botones()

    # ------------------------------------------------------------------ tabla
    def _cargar_tabla(self) -> None:
        self.filas.clear()
        datos = repo.listar_filas(
            curso_id=self._cursos[self._curso_prev].id,
            materia_id=self._materias[self.dd_materia.value].id,
        )
        self._cargando = True
        self.lista.controls = [
            self._dibujar_fila(i + 1, f) for i, f in enumerate(datos)
        ]
        self._cargando = False
        for fila in self.filas:
            self._refrescar(fila, actualizar=False)
        self._sucio = False
        self.lbl_info.value = f"{len(datos)} alumnos"

    def _actualizar_botones(self) -> None:
        self.btn_guardar.disabled = not self._sucio
        self.btn_descartar.disabled = not self._sucio
        self._actualizar(self.btn_guardar, self.btn_descartar)

    # ----------------------------------------------------------------- eventos
    def _al_editar(self, fila: _FilaUI) -> None:
        if self._cargando:
            return
        primera = not self._sucio
        self._sucio = True
        self.lbl_info.value = "Cambios sin guardar"
        self._actualizar(self.lbl_info)
        if primera:
            self._actualizar_botones()
        self._refrescar(fila)

    def _leer(self, fila: _FilaUI) -> tuple[dict, bool]:
        """Lee la fila de la UI. Devuelve (valores, todo_valido)."""
        valores, ok_total = {}, True
        for campo in CAMPOS_NOTA:
            v, ok = _parsear(fila.campos[campo].value)
            valores[campo] = v
            ok_total &= ok
        for campo in CAMPOS_AUS:
            valores[campo] = bool(fila.ausentes[campo].value)
        valores["cf_manual"], ok = _parsear_cf(fila.tf_cf.value)
        return valores, ok_total and ok

    def _refrescar(self, fila: _FilaUI, actualizar: bool = True) -> None:
        """Recalcula estado y CF con la capa de lógica de negocio y marca celdas."""
        v, _ = self._leer(fila)
        reg = RegistroNotas(
            Cuatrimestre(
                v["c1_nota1"], v["c1_nota2"], v["c1_int"], v["c1_cal"], v["c1_ausente"]
            ),
            Cuatrimestre(
                v["c2_nota1"], v["c2_nota2"], v["c2_int"], v["c2_cal"], v["c2_ausente"]
            ),
            v["if_nota"],
            v["if_ausente"],
            v["cf_manual"],
        )
        res = evaluar(reg)
        # La CF calculada se muestra como pista; si el docente escribe otra, manda esa.
        fila.tf_cf.hint_text = formatear_cf(res.cf_calculada)
        fila.tf_cf.border_color = C_ERROR if not _parsear_cf(fila.tf_cf.value)[1] else tema.BORDE
        fila.pastilla.content = tema.pastilla_estado(res.estado)
        # Ausente y sin nota cargada: se muestra el 4 por defecto como pista.
        for prefijo, cuat in (("c1", reg.c1), ("c2", reg.c2)):
            for sufijo in ("nota1", "nota2", "cal"):
                fila.campos[f"{prefijo}_{sufijo}"].hint_text = (
                    "4" if cuat.ausente else ""
                )
        cambiados = [fila.tf_cf, fila.pastilla]
        for campo, tf in fila.campos.items():
            _, ok = _parsear(tf.value)
            color = C_ERROR if not ok else tema.BORDE
            if ok and campo.endswith("_int"):
                cuat = reg.c1 if campo.startswith("c1") else reg.c2
                if (
                    necesita_intensificacion_cuatrimestral(cuat)
                    and cuat.intensificacion is None
                ):
                    color = C_AVISO
            elif ok and campo == "if_nota" and res.va_a_ifa and reg.if_nota is None and not reg.if_ausente:
                color = C_AVISO
            if tf.border_color != color or campo.endswith(("nota1", "nota2", "cal")):
                tf.border_color = color
                cambiados.append(tf)
        if actualizar:
            self._actualizar(*cambiados)

    def guardar(self, _e=None) -> bool:
        """Valida y guarda todas las filas. Devuelve True si se guardó."""
        lote, errores = [], 0
        for fila in self.filas:
            valores, ok = self._leer(fila)
            errores += 0 if ok else 1
            lote.append((fila.alumno_id, fila.materia_id, valores))
        if errores:
            tema.avisar(
                self.page,
                f"Hay {errores} alumno(s) con notas inválidas (en rojo). "
                f"Use enteros de {NOTA_MIN} a {NOTA_MAX} (la CF admite hasta 2 decimales) "
                f"o deje vacío.",
                error=True,
            )
            for fila in self.filas:
                self._refrescar(fila)
            return False
        repo.guardar_notas_lote(lote)
        self._sucio = False
        self.lbl_info.value = f"{len(self.filas)} alumnos"
        self._actualizar(self.lbl_info)
        self._actualizar_botones()
        tema.avisar(self.page, "Notas guardadas correctamente")
        return True
