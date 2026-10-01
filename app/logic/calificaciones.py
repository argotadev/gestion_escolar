"""Capa de lógica de negocio - reglas de calificación.

No accede a la base de datos ni a la GUI: recibe datos simples y devuelve
resultados, por lo que es fácil de testear.

Resumen del ciclo lectivo
-------------------------
Cada cuatrimestre tiene *Primer nota*, *Segunda nota* y, si alguna no se aprobó,
una *Intensificación cuatrimestral*. Luego el docente carga la *Calificación
del cuatrimestre* (``cal``): es una nota DEFINITIVA de cierre de etapa, cargada
a mano, que NO se calcula a partir de las notas previas.

Calificación Final (CF)::

    CF = (CC_1 + CC_2) / 2          (promedio exacto, hasta 2 decimales)

La CF es la que decide el estado final: Aprobado si CF >= NOTA_APROBACION,
Desaprobado si no. Si falta alguna CC el alumno queda Pendiente.

Decimales: la CF es la única nota con decimales (hasta 2). El valor calculado
es solo una propuesta: el docente puede corregirla a mano (``cf_manual``), y
en ese caso manda la nota cargada.

Ausentes en un cuatrimestre: si la CC está vacía cuenta como 4 en el promedio
(si el docente cargó una CC, se usa esa).

Intensificación Anual (IFA): es una etapa POSTERIOR e independiente. Van solo
los alumnos con CF < NOTA_APROBACION. Su nota se registra (va a otro informe)
pero no modifica la CF ni el estado final.

Estado final AUSENTE: solo si tuvo Aus. con CC vacía en los dos cuatrimestres
y además se marcó Aus. en la IFA (sin CF manual). Hasta que se marca el Aus.
de la IFA, ese alumno figura Desaprobado (CF 4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.config import NOTA_APROBACION, NOTA_AUSENTE, NOTA_MAX, NOTA_MIN


class Estado(str, Enum):
    """Estado consolidado de un alumno en una materia."""

    APROBADO = "Aprobado"
    DESAPROBADO = "Desaprobado"
    AUSENTE = "Ausente"                    # ausente en ambos cuatrimestres y en la IFA
    PENDIENTE = "Pendiente"                # faltan datos para decidir


@dataclass
class Cuatrimestre:
    """Datos cargados de un cuatrimestre. ``None`` = todavía sin cargar."""

    nota1: Optional[int] = None
    nota2: Optional[int] = None
    intensificacion: Optional[int] = None
    calificacion: Optional[int] = None     # Calificación del cuatrimestre
    ausente: bool = False


@dataclass
class RegistroNotas:
    """Todas las instancias de un alumno en una materia durante el año."""

    c1: Cuatrimestre = field(default_factory=Cuatrimestre)
    c2: Cuatrimestre = field(default_factory=Cuatrimestre)
    if_nota: Optional[int] = None
    if_ausente: bool = False               # no se presentó a la IFA
    cf_manual: Optional[float] = None      # CF corregida a mano (pisa la calculada)


@dataclass(frozen=True)
class Resultado:
    """Resultado de evaluar un :class:`RegistroNotas`."""

    estado: Estado
    calificacion_final: Optional[float]    # la que vale (manual o calculada)
    va_a_ifa: bool                         # CF < 7: debe rendir la IFA
    hubo_ausencia: bool
    cal_c1: Optional[int]
    cal_c2: Optional[int]
    cf_calculada: Optional[float] = None   # propuesta automática (sin la corrección manual)


# ---------------------------------------------------------------------------
# Funciones elementales
# ---------------------------------------------------------------------------
def aprueba(nota: Optional[float]) -> bool:
    """True si hay nota y alcanza la nota mínima de aprobación."""
    return nota is not None and nota >= NOTA_APROBACION


def nota_valida(nota: int) -> bool:
    """True si la nota es un entero dentro del rango permitido."""
    return isinstance(nota, int) and NOTA_MIN <= nota <= NOTA_MAX


def nota_efectiva(nota: Optional[int], ausente: bool) -> Optional[int]:
    """Aplica la regla del ausente: sin nota + ausente => 4 por defecto."""
    if nota is None and ausente:
        return NOTA_AUSENTE
    return nota


def necesita_intensificacion_cuatrimestral(c: Cuatrimestre) -> bool:
    """True si el alumno debe rendir la Intensificación cuatrimestral.

    Corresponde cuando alguna de las dos etapas (nota1/nota2) está cargada y
    no aprobada, o cuando estuvo ausente (su nota por defecto es 4).
    """
    n1 = nota_efectiva(c.nota1, c.ausente)
    n2 = nota_efectiva(c.nota2, c.ausente)
    return any(n is not None and not aprueba(n) for n in (n1, n2))


def calificacion_cuatrimestre(c: Cuatrimestre) -> Optional[int]:
    """Calificación de cierre del cuatrimestre (cargada a mano).

    NO es un promedio de nota1/nota2. Solo aplica la regla del ausente
    (sin calificación + ausente => 4).
    """
    return nota_efectiva(c.calificacion, c.ausente)


def estado_cuatrimestre(c: Cuatrimestre) -> Estado:
    """Estado de cierre de un cuatrimestre, según su CC (``calificacion``).

    Aus. manda sobre la CC cargada. N1, N2 e IFC no intervienen: la CC es la
    nota definitiva de la etapa.
    """
    if c.ausente:
        return Estado.AUSENTE
    if c.calificacion is None:
        return Estado.PENDIENTE
    return Estado.APROBADO if aprueba(c.calificacion) else Estado.DESAPROBADO


def calcular_calificacion_final(cal_c1: Optional[int], cal_c2: Optional[int]) -> Optional[float]:
    """Calificación Final (CF): ``(cal_c1 + cal_c2) / 2`` (promedio exacto).

    Devuelve ``None`` si falta alguna de las dos calificaciones.
    """
    if cal_c1 is None or cal_c2 is None:
        return None
    return round((cal_c1 + cal_c2) / 2, 2)


def ausente_todo_el_anio(reg: RegistroNotas) -> bool:
    """True si faltó a los dos cuatrimestres (sin CC) y también a la IFA."""
    return all(c.ausente and c.calificacion is None for c in (reg.c1, reg.c2)) and reg.if_ausente


def estado_ifa(reg: RegistroNotas) -> Estado:
    """Estado del alumno en la IFA (solo tiene sentido si ``va_a_ifa``).

    Ausente si se marcó Aus. en la IFA; Pendiente si todavía no tiene nota.
    """
    if reg.if_ausente:
        return Estado.AUSENTE
    if reg.if_nota is None:
        return Estado.PENDIENTE
    return Estado.APROBADO if aprueba(reg.if_nota) else Estado.DESAPROBADO


# ---------------------------------------------------------------------------
# Evaluación completa
# ---------------------------------------------------------------------------
def evaluar(reg: RegistroNotas) -> Resultado:
    """Determina el estado final y la CF de un alumno en una materia.

    Pasos:
    1. CF = promedio de las dos CC (ausente con CC vacía => 4).
       Si falta alguna CC queda "Pendiente".
    2. Si el docente cargó una CF a mano, esa reemplaza a la calculada.
    3. Estado según la CF: Aprobado (>= 7) o Desaprobado (< 7). Con CF < 7
       el alumno va a la IFA, cuya nota no cambia este resultado.
    4. Excepción: ausente en ambos cuatrimestres y en la IFA (sin CF manual)
       => AUSENTE.
    """
    cal1 = calificacion_cuatrimestre(reg.c1)
    cal2 = calificacion_cuatrimestre(reg.c2)
    hubo_ausencia = reg.c1.ausente or reg.c2.ausente
    calc = calcular_calificacion_final(cal1, cal2)
    cf = reg.cf_manual if reg.cf_manual is not None else calc
    if cf is None:
        return Resultado(Estado.PENDIENTE, None, False, hubo_ausencia, cal1, cal2, calc)
    va_a_ifa = not aprueba(cf)
    if reg.cf_manual is None and ausente_todo_el_anio(reg):
        estado = Estado.AUSENTE
    else:
        estado = Estado.APROBADO if aprueba(cf) else Estado.DESAPROBADO
    return Resultado(estado, cf, va_a_ifa, hubo_ausencia, cal1, cal2, calc)


def formatear_cf(cf: Optional[float]) -> str:
    """7.0 -> '7', 7.5 -> '7,5', 7.25 -> '7,25', None -> ''."""
    if cf is None:
        return ""
    return f"{cf:.2f}".rstrip("0").rstrip(".").replace(".", ",")
