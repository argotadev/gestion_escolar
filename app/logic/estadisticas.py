"""Capa de lógica de negocio - agregados para los informes.

Clasifica cada :class:`~app.logic.calificaciones.Resultado` en tres categorías
mutuamente excluyentes, de modo que Aprobados + Desaprobados + Ausentes suman
el total (salvo los registros aún ``Pendiente``):

* **Aprobados**    -> estado ``APROBADO`` (CF >= 7).
* **Ausentes**     -> ``AUSENTE``: ausente en ambos cuatrimestres y en la IFA.
* **Desaprobados** -> ``DESAPROBADO`` (CF < 7; la nota de la IFA no lo cambia).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.logic.calificaciones import (
    Estado, RegistroNotas, Resultado, estado_cuatrimestre, estado_ifa, evaluar,
)


@dataclass
class Resumen:
    """Conteos de un grupo (curso/división, materia, año...)."""

    total: int = 0
    aprobados: int = 0
    desaprobados: int = 0
    ausentes: int = 0
    pendientes: int = 0

    def agregar(self, r: Resultado) -> None:
        self.agregar_estado(r.estado)

    def agregar_estado(self, estado: Estado) -> None:
        self.total += 1
        if estado == Estado.APROBADO:
            self.aprobados += 1
        elif estado == Estado.AUSENTE:
            self.ausentes += 1
        elif estado == Estado.DESAPROBADO:
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


def resumir_cuatrimestre(registros: Iterable[RegistroNotas], numero: int) -> Resumen:
    """Resumen del 1.er (``numero=1``) o 2.º (``numero=2``) cuatrimestre.

    Usa el estado de cierre del cuatrimestre (ver
    :func:`~app.logic.calificaciones.estado_cuatrimestre`).
    """
    resumen = Resumen()
    for reg in registros:
        resumen.agregar_estado(estado_cuatrimestre(reg.c1 if numero == 1 else reg.c2))
    return resumen


def resumir_ifa(registros: Iterable[RegistroNotas]) -> Resumen:
    """Resumen de la IFA: cuenta solo a quienes deben rendirla (CF < 7).

    No se usa en el informe .docx; es una vista aparte del Consolidado.
    """
    resumen = Resumen()
    for reg in registros:
        if evaluar(reg).va_a_ifa:
            resumen.agregar_estado(estado_ifa(reg))
    return resumen


# ---------------------------------------------------------------------------
# Agrupaciones usadas por el informe departamental
# ---------------------------------------------------------------------------
def agrupar_por_materia_y_curso(filas) -> dict[tuple[str, int, int], Resumen]:
    """Agrupa por ``(materia, año, división)``.

    ``filas`` es un iterable de objetos con ``.materia``, ``.curso`` (con
    ``anio`` y ``division``) y ``.registro`` (RegistroNotas).
    """
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
