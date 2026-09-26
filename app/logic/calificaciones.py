"""Capa de lógica de negocio - reglas de calificación.

No accede a la base de datos ni a la GUI: recibe datos simples y devuelve
resultados, por lo que es fácil de testear.

Resumen del ciclo lectivo
-------------------------
Cada cuatrimestre tiene *Primer nota*, *Segunda nota* y, si alguna no se aprobó,
una *Intensificación cuatrimestral*. Luego el docente carga la *Calificación
del cuatrimestre* (``cal``): es una nota DEFINITIVA de cierre de etapa, cargada
a mano, que NO se calcula a partir de las notas previas.

Al final del año existen dos flujos excluyentes para la Calificación Final:

    Flujo normal (aprobó ambos cuatrimestres y nunca estuvo ausente)::

        CF = (CAL_1 + CAL_2) / 2          (promedio exacto, hasta 2 decimales)

    Flujo Intensificación Final (IF) (no aprobó alguno de los dos cuatrimestres,
    o estuvo ausente)::

        CF = NOTA_IF          (solo la nota de la IF; no se promedia con nada)

Decimales: la CF es la única nota con decimales (hasta 2). El valor calculado
es solo una propuesta: el docente puede corregirla a mano (``cf_manual``), y
en ese caso manda la nota cargada. Aprueba si CF >= NOTA_APROBACION.

Ausentes: todo alumno ausente tiene nota 4 por defecto (menor que la nota de
aprobación), pasa directo a la IF y, aunque tenga 100 % de inasistencia, puede
presentarse a la IF y aprobar. Si no aprueba (o no se presenta: nota 4),
engrosa la lista de desaprobados.
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
    A_IF = "A IF"                          # debe rendir IF, aún sin nota
    A_IF_AUSENTE = "A IF (ausente)"        # ídem, pero por ausencia
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
    if_ausente: bool = False               # no se presentó a la IF
    cf_manual: Optional[float] = None      # CF corregida a mano (pisa la calculada)


@dataclass(frozen=True)
class Resultado:
    """Resultado de evaluar un :class:`RegistroNotas`."""

    estado: Estado
    calificacion_final: Optional[float]    # la que vale (manual o calculada)
    va_a_if: bool
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


def cuatrimestre_desaprobado(c: Cuatrimestre) -> bool:
    """True si el cuatrimestre no fue aprobado (ausencia o cal. < aprobación)."""
    if c.ausente:
        return True
    cal = calificacion_cuatrimestre(c)
    return cal is not None and not aprueba(cal)


def calcular_calificacion_final(
    cal_c1: Optional[int],
    cal_c2: Optional[int],
    va_a_if: bool,
    nota_if: Optional[int] = None,
) -> Optional[float]:
    """Calificación Final (CF) del alumno en la materia.

    Fórmula (ver docstring del módulo):

    * Si ``va_a_if``:  ``CF = nota_if``  (exclusivamente la nota de la IF).
    * Si no:           ``CF = (cal_c1 + cal_c2) / 2`` (promedio exacto).

    Devuelve ``None`` si falta algún dato necesario.
    """
    if va_a_if:
        return nota_if
    if cal_c1 is None or cal_c2 is None:
        return None
    return round((cal_c1 + cal_c2) / 2, 2)


# ---------------------------------------------------------------------------
# Evaluación completa
# ---------------------------------------------------------------------------
def evaluar(reg: RegistroNotas) -> Resultado:
    """Determina el estado y la CF de un alumno en una materia.

    Pasos:
    1. Ausente en cualquier cuatrimestre  -> va a IF.
    2. Cuatrimestre desaprobado (cal < 7) -> va a IF ("no aprobó ambos").
    3. Si va a IF: la CF es la nota de la IF; si no se presentó a la IF su
       nota por defecto es 4 (=> desaprobado). Sin nota IF queda "A IF".
    4. Si no va a IF y ambas calificaciones están cargadas: CF = promedio.
       Si falta alguna, queda "Pendiente".
    5. Si el docente cargó una CF a mano, esa reemplaza a la calculada.
    """
    cal1 = calificacion_cuatrimestre(reg.c1)
    cal2 = calificacion_cuatrimestre(reg.c2)
    hubo_ausencia = reg.c1.ausente or reg.c2.ausente
    va_a_if = cuatrimestre_desaprobado(reg.c1) or cuatrimestre_desaprobado(reg.c2)

    if va_a_if:
        nota_if = NOTA_AUSENTE if reg.if_ausente else reg.if_nota
        calc = calcular_calificacion_final(cal1, cal2, True, nota_if)
        cf = reg.cf_manual if reg.cf_manual is not None else calc
        if cf is None:
            estado = Estado.A_IF_AUSENTE if hubo_ausencia else Estado.A_IF
        else:
            estado = Estado.APROBADO if aprueba(cf) else Estado.DESAPROBADO
        return Resultado(estado, cf, True, hubo_ausencia, cal1, cal2, calc)

    calc = calcular_calificacion_final(cal1, cal2, False)
    cf = reg.cf_manual if reg.cf_manual is not None else calc
    if cf is None:
        return Resultado(Estado.PENDIENTE, None, False, hubo_ausencia, cal1, cal2, calc)
    estado = Estado.APROBADO if aprueba(cf) else Estado.DESAPROBADO
    return Resultado(estado, cf, False, hubo_ausencia, cal1, cal2, calc)


def formatear_cf(cf: Optional[float]) -> str:
    """7.0 -> '7', 7.5 -> '7,5', 7.25 -> '7,25', None -> ''."""
    if cf is None:
        return ""
    return f"{cf:.2f}".rstrip("0").rstrip(".").replace(".", ",")
