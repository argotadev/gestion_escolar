"""Vista 2 - Consolidado de estado (Aprobado / Desaprobado / A IF) - Flet."""
from __future__ import annotations

import flet as ft

from app.data import repository as repo
from app.logic.calificaciones import Estado, evaluar, formatear_cf
from app.ui import tema
from app.ui.comun import etiqueta_curso

TODOS, TODAS = "todos", "todas"
POR_PAGINA = 100

# (título, expand o ancho fijo, alineación)
COLUMNAS = [("Alumno", 3, "izq"), ("Curso", 70, "cen"), ("Materia", 4, "izq"),
            ("Cal. 1.er C.", 90, "cen"), ("Cal. 2.º C.", 90, "cen"), ("Nota IF", 80, "cen"),
            ("CF", 60, "cen"), ("Estado", 150, "cen")]


def _celda(ctrl: ft.Control, ancho, alin: str) -> ft.Container:
    a = ft.Alignment.CENTER_LEFT if alin == "izq" else ft.Alignment.CENTER
    if isinstance(ancho, int) and ancho > 20:
        return ft.Container(ctrl, width=ancho, alignment=a)
    return ft.Container(ctrl, expand=ancho, alignment=a)


class VistaConsolidado:
    def __init__(self, page: ft.Page):
        self.page = page
        self.cursos = repo.listar_cursos()
        self._cursos = {str(c.id): c for c in self.cursos}
        self._pagina = 0
        self._filtradas: list[tuple] = []

        self.dd_curso = tema.desplegable(
            "Curso", [(TODOS, "Todos los cursos")] + [(str(c.id), etiqueta_curso(c)) for c in self.cursos],
            str(self.cursos[0].id), 290, self._al_elegir_curso)
        self.dd_materia = tema.desplegable("Materia", [(TODAS, "Todas")], TODAS, 360, self._al_filtrar)
        self.dd_estado = tema.desplegable(
            "Estado", [(TODOS, "Todos")] + [(e.value, e.value) for e in Estado], TODOS, 190, self._al_filtrar)

        self._stats = {k: ft.Text("0", size=26, weight=ft.FontWeight.W_700) for k in
                       ("total", "aprobados", "desaprobados", "a_if", "pendientes")}
        self._sub_aif = ft.Text(" ", size=12, color=tema.TEXTO_SUAVE)
        tarjetas = ft.Row([
            self._tarjeta_stat("Total", "total", tema.TEXTO),
            self._tarjeta_stat("Aprobados", "aprobados", tema.COLOR_ESTADO[Estado.APROBADO][0]),
            self._tarjeta_stat("Desaprobados", "desaprobados", tema.COLOR_ESTADO[Estado.DESAPROBADO][0]),
            self._tarjeta_stat("A IF", "a_if", tema.COLOR_ESTADO[Estado.A_IF][0], self._sub_aif),
            self._tarjeta_stat("Pendientes", "pendientes", tema.COLOR_ESTADO[Estado.PENDIENTE][0]),
        ], spacing=14)

        encabezado = ft.Container(
            ft.Row([_celda(ft.Text(t, size=12, weight=ft.FontWeight.W_700, color=tema.TEXTO_SUAVE), w, a)
                    for t, w, a in COLUMNAS], spacing=0),
            padding=ft.Padding.symmetric(vertical=10, horizontal=12), bgcolor=tema.FILA_ALTERNA,
            border_radius=ft.BorderRadius.only(top_left=10, top_right=10))
        self.lista = ft.ListView(expand=True, spacing=0)

        self.lbl_pagina = ft.Text("", size=12.5, color=tema.TEXTO_SUAVE)
        self.btn_ant = ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _e: self._ir(-1), tooltip="Anterior")
        self.btn_sig = ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda _e: self._ir(1), tooltip="Siguiente")
        pie = ft.Row([self.lbl_pagina, ft.Container(expand=True), self.btn_ant, self.btn_sig])

        barra = ft.Row([self.dd_curso, self.dd_materia, self.dd_estado, ft.Container(expand=True),
                        tema.boton_secundario("Actualizar", ft.Icons.REFRESH, lambda _e: self.actualizar())],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        self.control = ft.Column([
            tema.titulo_pagina("Consolidado de estado",
                               "Situación de cada alumno según las reglas de calificación."),
            tema.tarjeta(barra, padding=14),
            tarjetas,
            tema.tarjeta(ft.Column([encabezado, ft.Divider(height=1, color=tema.BORDE), self.lista, pie],
                                   spacing=0, expand=True),
                         padding=ft.Padding.only(left=6, right=6, top=6, bottom=2), expand=True),
        ], spacing=16, expand=True)
        self._cargar_materias()
        self.actualizar(montada=False)

    def _tarjeta_stat(self, titulo: str, clave: str, color: str, extra: ft.Control | None = None):
        self._stats[clave].color = color
        cuerpo = [ft.Text(titulo, size=12.5, color=tema.TEXTO_SUAVE), self._stats[clave]]
        if extra is not None:
            cuerpo.append(extra)
        return tema.tarjeta(ft.Column(cuerpo, spacing=0), padding=ft.Padding.symmetric(horizontal=18, vertical=12),
                            expand=True, height=92)

    def _actualizar(self, *controles: ft.Control) -> None:
        for c in controles:
            try:
                c.update()
            except RuntimeError:
                pass

    # ---------------------------------------------------------------- eventos
    def _cargar_materias(self) -> None:
        curso = self._cursos.get(self.dd_curso.value)
        materias = repo.listar_materias() if curso is None else repo.listar_materias_de_curso(curso.id)
        self._materias = {str(m.id): m for m in materias}
        self.dd_materia.options = [ft.DropdownOption(key=TODAS, text="Todas")] + [
            ft.DropdownOption(key=str(m.id), text=m.nombre) for m in materias]
        self.dd_materia.value = TODAS

    def _al_elegir_curso(self, _e) -> None:
        self._cargar_materias()
        self._actualizar(self.dd_materia)
        self.actualizar()

    def _al_filtrar(self, _e) -> None:
        self.actualizar()

    def al_mostrar(self) -> None:
        self.actualizar()

    def _ir(self, delta: int) -> None:
        self._pagina += delta
        self._dibujar_pagina()
        self._actualizar(self.lista, self.lbl_pagina, self.btn_ant, self.btn_sig)

    # ------------------------------------------------------------------ datos
    def actualizar(self, montada: bool = True) -> None:
        curso = self._cursos.get(self.dd_curso.value)
        materia = self._materias.get(self.dd_materia.value)
        filtro = self.dd_estado.value
        filas = repo.listar_filas(curso.id if curso else None, materia.id if materia else None)

        cuenta = {e: 0 for e in Estado}
        self._filtradas = []
        for f in filas:
            r = evaluar(f.registro)
            cuenta[r.estado] += 1
            if filtro == TODOS or r.estado.value == filtro:
                self._filtradas.append((f, r))

        self._stats["total"].value = f"{len(filas):,}".replace(",", ".")
        self._stats["aprobados"].value = str(cuenta[Estado.APROBADO])
        self._stats["desaprobados"].value = str(cuenta[Estado.DESAPROBADO])
        self._stats["a_if"].value = str(cuenta[Estado.A_IF] + cuenta[Estado.A_IF_AUSENTE])
        self._sub_aif.value = f"{cuenta[Estado.A_IF_AUSENTE]} por ausencia"
        self._stats["pendientes"].value = str(cuenta[Estado.PENDIENTE])

        self._pagina = 0
        self._dibujar_pagina()
        if montada:
            self._actualizar(self.lista, self.lbl_pagina, self.btn_ant, self.btn_sig,
                             *self._stats.values(), self._sub_aif)

    def _dibujar_pagina(self) -> None:
        total = len(self._filtradas)
        paginas = max(1, -(-total // POR_PAGINA))
        self._pagina = min(max(self._pagina, 0), paginas - 1)
        ini = self._pagina * POR_PAGINA
        trozo = self._filtradas[ini:ini + POR_PAGINA]

        def num(v):
            return formatear_cf(v) if isinstance(v, float) else ("" if v is None else str(v))

        filas = []
        for i, (f, r) in enumerate(trozo):
            reg = f.registro
            valores = [
                ft.Text(f.nombre_completo, size=13.5, color=tema.TEXTO, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f.curso.etiqueta, size=13, color=tema.TEXTO_SUAVE),
                ft.Text(f.materia, size=13.5, color=tema.TEXTO, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(num(r.cal_c1), size=13.5), ft.Text(num(r.cal_c2), size=13.5),
                ft.Text("Aus." if reg.if_ausente else num(reg.if_nota), size=13.5),
                ft.Text(num(r.calificacion_final), size=14, weight=ft.FontWeight.W_700),
                tema.pastilla_estado(r.estado),
            ]
            filas.append(ft.Container(
                ft.Row([_celda(v, w, a) for v, (_, w, a) in zip(valores, COLUMNAS)], spacing=0),
                padding=ft.Padding.symmetric(vertical=6, horizontal=12),
                bgcolor=tema.FILA_ALTERNA if i % 2 else "#FFFFFF"))
        self.lista.controls = filas
        desde = ini + 1 if total else 0
        self.lbl_pagina.value = (f"Mostrando {desde}–{ini + len(trozo)} de {total}  ·  "
                                 f"página {self._pagina + 1} de {paginas}")
        self.btn_ant.disabled = self._pagina == 0
        self.btn_sig.disabled = self._pagina >= paginas - 1
