"""Vista Análisis - gráficos por etapa para curso, departamento o toda la escuela - Flet.

Es un análisis aparte: no modifica el Consolidado ni el informe .docx.
"""
from __future__ import annotations

import flet as ft

from app.config import MATERIAS_RIESGO
from app.data import repository as repo
from app.logic import analisis
from app.logic.calificaciones import Estado
from app.logic.estadisticas import ETAPA_FINAL, ETAPA_IFA, ETAPAS
from app.ui import graficos, tema
from app.ui.comun import etiqueta_curso

CURSO, DEPARTAMENTO, ESCUELA = "curso", "departamento", "escuela"
AMBITOS = [(CURSO, "Curso"), (DEPARTAMENTO, "Departamento"), (ESCUELA, "Toda la escuela")]
TODAS = "todas"
ALTO_MAX_COMPARACION = 396   # px; unas 11 barras
POR_MATERIA, POR_CURSO, POR_DEPARTAMENTO = "materia", "curso", "departamento"
# Agrupaciones que tienen sentido en cada ámbito (en un curso no hay cursos que comparar).
AGRUPACIONES = {
    CURSO: [(POR_MATERIA, "Materia")],
    DEPARTAMENTO: [(POR_MATERIA, "Materia"), (POR_CURSO, "Curso")],
    ESCUELA: [(POR_DEPARTAMENTO, "Departamento"), (POR_MATERIA, "Materia"), (POR_CURSO, "Curso")],
}


def _titulo_tarjeta(titulo: str, subtitulo: ft.Text | str) -> ft.Control:
    if isinstance(subtitulo, str):
        subtitulo = ft.Text(subtitulo, size=14.5, color=tema.TEXTO_SUAVE)
    return ft.Column([ft.Text(titulo, size=18, weight=ft.FontWeight.W_700, color=tema.TEXTO), subtitulo],
                     spacing=2, expand=True)


class VistaAnalisis:
    def __init__(self, page: ft.Page):
        self.page = page
        self.cursos = repo.listar_cursos()
        self._cursos = {str(c.id): c for c in self.cursos}
        self.departamentos = repo.listar_departamentos()
        self._departamentos = {str(d.id): d for d in self.departamentos}
        self.materias = repo.listar_materias()
        nombre_depto = {d.id: d.nombre for d in self.departamentos}
        self._depto_de_materia = {m.id: nombre_depto.get(m.departamento_id, "") for m in self.materias}
        self._filas: list = []

        # ---- filtros
        self.dd_ambito = tema.desplegable("Ámbito", AMBITOS, CURSO, 180, self._al_cambiar_ambito)
        self.dd_curso = tema.desplegable(
            "Curso", [(str(c.id), etiqueta_curso(c)) for c in self.cursos], str(self.cursos[0].id), 260,
            self._al_cambiar_alcance)
        self.dd_depto = tema.desplegable(
            "Departamento", [(str(d.id), d.nombre) for d in self.departamentos],
            str(self.departamentos[0].id), 360, self._al_cambiar_alcance)
        self.dd_depto.visible = False
        self.dd_materia = tema.desplegable("Materia", [(TODAS, "Todas")], TODAS, 300, self._al_filtrar)
        barra = ft.Row([self.dd_ambito, self.dd_curso, self.dd_depto, self.dd_materia, ft.Container(expand=True),
                        tema.boton_secundario("Actualizar", ft.Icons.REFRESH, lambda _e: self.actualizar())],
                       spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # ---- 1. la cursada etapa por etapa
        self.col_etapas = ft.Column(spacing=10)
        tarjeta_etapas = tema.tarjeta(ft.Column([
            _titulo_tarjeta("La cursada etapa por etapa",
                            "Porcentaje de notas (alumno × materia) en cada estado. "
                            "La IFA cuenta solo a quienes tienen CF < 7."),
            self.col_etapas, graficos.leyenda()], spacing=14), padding=20)

        # ---- 2. comparación entre grupos
        self.dd_etapa = tema.desplegable("Etapa", ETAPAS, ETAPA_FINAL, 180, self._al_cambiar_comparacion)
        self.dd_agrupar = tema.desplegable("Agrupar por", AGRUPACIONES[CURSO], POR_MATERIA, 170,
                                           self._al_cambiar_comparacion)
        self.lbl_comparacion = ft.Text("", size=14.5, color=tema.TEXTO_SUAVE)
        self.lista_comparacion = ft.ListView(spacing=8)
        tarjeta_comparacion = tema.tarjeta(ft.Column([
            ft.Row([_titulo_tarjeta("Comparación", self.lbl_comparacion), self.dd_etapa, self.dd_agrupar],
                   spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
            self.lista_comparacion, graficos.leyenda()], spacing=14), padding=20, expand=True)

        # ---- 3. distribución de notas
        self.dd_nota = tema.desplegable("Nota", analisis.NOTAS, analisis.NOTA_CF, 220, self._al_cambiar_histograma)
        self.cont_histograma = ft.Container()
        self.lbl_histograma = ft.Text("", size=14.5, color=tema.TEXTO_SUAVE)
        tarjeta_histograma = tema.tarjeta(ft.Column([
            ft.Row([_titulo_tarjeta("Distribución de notas",
                                    "Cantidad de notas por valor; 6 = de 6 a 6,99."), self.dd_nota],
                   spacing=10, vertical_alignment=ft.CrossAxisAlignment.START),
            self.cont_histograma, self.lbl_histograma], spacing=14), padding=20, expand=True)

        # ---- 4. del 1.er al 2.º cuatrimestre
        self.cont_matriz = ft.Container()
        self.lbl_matriz = ft.Text("", size=14.5, color=tema.TEXTO)
        tarjeta_matriz = tema.tarjeta(ft.Column([
            _titulo_tarjeta("Del 1.er al 2.º cuatrimestre",
                            "Cada fila suma 100 %: qué pasó en el 2.º cuatrimestre con quienes tenían "
                            "ese estado en el 1.º."),
            ft.Row([self.cont_matriz], scroll=ft.ScrollMode.AUTO), self.lbl_matriz], spacing=14),
            padding=20, expand=True)

        # ---- 5. alumnos en riesgo
        self.cont_riesgo = ft.Container()
        self.lbl_riesgo = ft.Text("", size=15, weight=ft.FontWeight.W_600, color=tema.TEXTO)
        self.lista_riesgo = ft.ListView(spacing=0)
        tarjeta_riesgo = tema.tarjeta(ft.Column([
            _titulo_tarjeta("Alumnos en riesgo",
                            f"Alumnos según cuántas materias del ámbito tienen con CF < 7. "
                            f"En riesgo: {MATERIAS_RIESGO} o más."),
            self.cont_riesgo, self.lbl_riesgo, self.lista_riesgo], spacing=14), padding=20, expand=True)

        self.control = ft.Column([
            tema.titulo_pagina("Análisis", "Situación de aprobados, desaprobados, ausentes e IFA en cada etapa "
                                           "de la cursada. No modifica el informe."),
            tema.tarjeta(barra, padding=14),
            tarjeta_etapas,
            ft.Row([tarjeta_comparacion, tarjeta_histograma], spacing=16,
                   vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row([tarjeta_matriz, tarjeta_riesgo], spacing=16,
                   vertical_alignment=ft.CrossAxisAlignment.START),
        ], spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)
        self._cargar_materias()
        self.actualizar(montada=False)

    # ---------------------------------------------------------------- eventos
    def _al_cambiar_ambito(self, _e) -> None:
        ambito = self.dd_ambito.value
        self.dd_curso.visible = ambito == CURSO
        self.dd_depto.visible = ambito == DEPARTAMENTO
        opciones = AGRUPACIONES[ambito]
        self.dd_agrupar.options = [ft.DropdownOption(key=k, text=t) for k, t in opciones]
        self.dd_agrupar.value = opciones[0][0]
        self._al_cambiar_alcance(None)

    def _al_cambiar_alcance(self, _e) -> None:
        self._cargar_materias()
        self.actualizar()

    def _al_filtrar(self, _e) -> None:
        self.actualizar()

    def _al_cambiar_comparacion(self, _e) -> None:
        self._dibujar_comparacion()
        self._refrescar()

    def _al_cambiar_histograma(self, _e) -> None:
        self._dibujar_histograma()
        self._refrescar()

    def al_mostrar(self) -> None:
        self.actualizar()

    def _refrescar(self) -> None:
        try:
            self.control.update()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ datos
    def _cargar_materias(self) -> None:
        ambito = self.dd_ambito.value
        if ambito == CURSO:
            materias = repo.listar_materias_de_curso(self._cursos[self.dd_curso.value].id)
        elif ambito == DEPARTAMENTO:
            depto = self._departamentos[self.dd_depto.value].id
            materias = [m for m in self.materias if m.departamento_id == depto]
        else:
            materias = self.materias
        self._materias = {str(m.id): m for m in materias}
        self.dd_materia.options = [ft.DropdownOption(key=TODAS, text="Todas")] + [
            ft.DropdownOption(key=str(m.id), text=m.nombre) for m in materias]
        self.dd_materia.value = TODAS

    def actualizar(self, montada: bool = True) -> None:
        ambito = self.dd_ambito.value
        materia = self._materias.get(self.dd_materia.value)
        filtros = {"materia_id": materia.id if materia else None}
        if ambito == CURSO:
            filtros["curso_id"] = self._cursos[self.dd_curso.value].id
        elif ambito == DEPARTAMENTO:
            filtros["departamento_id"] = self._departamentos[self.dd_depto.value].id
        self._filas = repo.listar_filas(**filtros)

        self._dibujar_etapas()
        self._dibujar_comparacion()
        self._dibujar_histograma()
        self._dibujar_matriz()
        self._dibujar_riesgo()
        if montada:
            self._refrescar()

    # ---------------------------------------------------------------- dibujo
    def _dibujar_etapas(self) -> None:
        registros = [f.registro for f in self._filas]
        self.col_etapas.controls = [graficos.fila_barra(nombre, r)
                                    for _, nombre, r in analisis.resumen_por_etapa(registros)]

    def _dibujar_comparacion(self) -> None:
        agrupar = self.dd_agrupar.value
        clave = {
            POR_MATERIA: lambda f: f.materia,
            POR_CURSO: lambda f: f.curso.etiqueta,
            POR_DEPARTAMENTO: lambda f: self._depto_de_materia.get(f.materia_id, ""),
        }[agrupar]
        etapa = self.dd_etapa.value
        grupos = analisis.resumen_por_grupo(self._filas, clave, lambda f: f.registro, etapa)
        nombre_etapa = dict(ETAPAS)[etapa]
        aclaracion = " (solo alumnos con CF < 7)" if etapa == ETAPA_IFA else ""
        self.lbl_comparacion.value = (f"Etapa {nombre_etapa}{aclaracion}, ordenado de más a menos "
                                      f"desaprobados.")
        self.lista_comparacion.controls = (
            [graficos.fila_barra(nombre, r, ancho_rotulo=210, pct_min_rotulo=17) for nombre, r in grupos]
            or [ft.Text("No hay notas en esta etapa.", size=15, color=tema.TEXTO_SUAVE)])
        # Crece con los grupos hasta un máximo; más allá, la lista se desplaza.
        self.lista_comparacion.height = min(ALTO_MAX_COMPARACION, max(1, len(grupos)) * 36)

    def _dibujar_histograma(self) -> None:
        h = analisis.histograma((f.registro for f in self._filas), self.dd_nota.value)
        self.cont_histograma.content = graficos.histograma(h)
        if h.con_nota:
            pct = graficos.fmt_pct(100 * h.zona_limite / h.con_nota)
            n = graficos.fmt_num
            self.lbl_histograma.value = (f"Zona límite (6 a 6,99): {n(h.zona_limite)} de {n(h.con_nota)} notas "
                                         f"({pct}).  ·  Sin nota cargada: {n(h.sin_nota)}.")
        else:
            self.lbl_histograma.value = f"No hay notas cargadas. Sin nota: {graficos.fmt_num(h.sin_nota)}."

    def _dibujar_matriz(self) -> None:
        t = analisis.transiciones(f.registro for f in self._filas)
        self.cont_matriz.content = graficos.matriz_transiciones(t)
        n, pct = graficos.fmt_num, graficos.fmt_pct
        frases = []
        for desde, hacia, verbo in ((Estado.DESAPROBADO, Estado.APROBADO, "aprobaron"),
                                    (Estado.APROBADO, Estado.DESAPROBADO, "desaprobaron")):
            if t.total_fila(desde):
                frases.append(f"De los {n(t.total_fila(desde))} {desde.value.lower()}s del 1.er C., "
                              f"{n(t.cantidad(desde, hacia))} {verbo} el 2.º ({pct(t.pct_fila(desde, hacia))}).")
        self.lbl_matriz.value = "\n".join(frases)

    def _dibujar_riesgo(self) -> None:
        if self.dd_materia.value != TODAS:
            self.cont_riesgo.content = ft.Text("Elegí “Todas” en Materia para ver este gráfico.",
                                               size=15, color=tema.TEXTO_SUAVE)
            self.lbl_riesgo.value, self.lista_riesgo.controls, self.lista_riesgo.height = "", [], 0
            return
        r = analisis.riesgo(self._filas)
        self.cont_riesgo.content = graficos.barras_riesgo(r)
        self.lbl_riesgo.value = (f"{graficos.fmt_num(len(r.en_riesgo))} alumnos con {MATERIAS_RIESGO} "
                                 f"o más materias con CF < 7")
        filas = []
        for i, a in enumerate(r.en_riesgo):
            filas.append(ft.Container(ft.Row([
                ft.Container(ft.Text(a.nombre, size=15, color=tema.TEXTO, no_wrap=True,
                                     overflow=ft.TextOverflow.ELLIPSIS), width=200),
                ft.Container(ft.Text(a.curso, size=14.5, color=tema.TEXTO_SUAVE), width=70),
                ft.Container(ft.Text(str(len(a.materias)), size=15, weight=ft.FontWeight.W_700,
                                     color=tema.TEXTO), width=28, alignment=ft.Alignment.CENTER),
                ft.Text(", ".join(a.materias), size=14, color=tema.TEXTO_SUAVE, expand=True,
                        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, tooltip=", ".join(a.materias)),
            ], spacing=10), padding=ft.Padding.symmetric(vertical=6, horizontal=8),
                bgcolor=tema.FILA_ALTERNA if i % 2 else None, border_radius=6))
        self.lista_riesgo.controls = filas
        self.lista_riesgo.height = min(ALTO_MAX_COMPARACION, len(filas) * 36)
