"""Capa de lógica de negocio - agregados para los informes.

Clasifica cada :class:`~app.logic.calificaciones.Resultado` en tres categorías
mutuamente excluyentes, de modo que Aprobados + Desaprobados + Ausentes suman
el total (salvo los registros aún ``Pendiente``):

* **Aprobados**    -> estado ``APROBADO`` (por promedio o por IF).
* **Ausentes**     -> ``A_IF_AUSENTE``: alumno ausente que aún puede aprobar
  en la IF ("intensificador"). Si rinde la IF pasa a Aprobado o Desaprobado.
* **Desaprobados** -> ``DESAPROBADO`` y ``A_IF`` (no aprobó ambas etapas y no
  estaba ausente: engrosa la lista de desaprobados hasta que apruebe la IF).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.logic.calificaciones import Estado, Resultado


@dataclass
class Resumen:
    """Conteos de un grupo (curso/división, materia, año...)."""

    total: int = 0
    aprobados: int = 0
    desaprobados: int = 0
    ausentes: int = 0
    pendientes: int = 0

    def agregar(self, r: Resultado) -> None:
        self.total += 1
        if r.estado == Estado.APROBADO:
            self.aprobados += 1
        elif r.estado == Estado.A_IF_AUSENTE:
            self.ausentes += 1
        elif r.estado in (Estado.DESAPROBADO, Estado.A_IF):
            self.desaprobados += 1
        else:
            self.pendientes += 1

    def sumar(self, otro: "Resumen") -> None:
        self.total += otro.total
        self.aprobados += otro.aprobados
        self.desaprobados += otro.desaprobados
        self.ausentes += otro.ausentes
        self.pendientes += otro.pendientes

    def porcentaje(self, cantidad: int) -> float:
        """Porcentaje sobre el total de alumnos (0.0 si el grupo está vacío)."""
        return 100.0 * cantidad / self.total if self.total else 0.0

    @property
    def pct_aprobados(self) -> float:
        return self.porcentaje(self.aprobados)

    @property
    def pct_desaprobados(self) -> float:
        return self.porcentaje(self.desaprobados)

    @property
    def pct_ausentes(self) -> float:
        return self.porcentaje(self.ausentes)


def resumir(resultados: Iterable[Resultado]) -> Resumen:
    """Agrega una colección de resultados en un :class:`Resumen`."""
    resumen = Resumen()
    for r in resultados:
        resumen.agregar(r)
    return resumen


# ---------------------------------------------------------------------------
# Agrupaciones usadas por el informe departamental
# ---------------------------------------------------------------------------
def agrupar_por_materia_y_curso(filas) -> dict[tuple[str, int, int], Resumen]:
    """Agrupa por ``(materia, año, división)``.

    ``filas`` es un iterable de objetos con ``.materia``, ``.curso`` (con
    ``anio`` y ``division``) y ``.registro`` (RegistroNotas).
    """
    from app.logic.calificaciones import evaluar  # import local: evita ciclos

    grupos: dict[tuple[str, int, int], Resumen] = {}
    for f in filas:
        clave = (f.materia, f.curso.anio, f.curso.division)
        grupos.setdefault(clave, Resumen()).agregar(evaluar(f.registro))
    return grupos


def agrupar_por_anio(grupos: dict[tuple[str, int, int], Resumen]) -> dict[int, Resumen]:
    """Suma los resúmenes de todas las materias/divisiones de cada año."""
    por_anio: dict[int, Resumen] = {}
    for (_, anio, _), resumen in grupos.items():
        por_anio.setdefault(anio, Resumen()).sumar(resumen)
    return por_anio
