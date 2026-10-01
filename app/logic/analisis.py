"""Capa de lógica de negocio - datos para los gráficos de la vista Análisis.

Es un análisis aparte: no interviene en el informe .docx. Reutiliza las reglas
de :mod:`app.logic.calificaciones` y los conteos de :mod:`app.logic.estadisticas`,
así que las cifras coinciden con las del Consolidado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, TypeVar

from app.config import MATERIAS_RIESGO, NOTA_APROBACION, NOTA_MAX, NOTA_MIN, ZONA_LIMITE_DESDE
from app.logic.calificaciones import Estado, RegistroNotas, estado_cuatrimestre, evaluar
from app.logic.estadisticas import ETAPAS, Resumen, resumir_etapa

T = TypeVar("T")

NOTA_CF, NOTA_CC1, NOTA_CC2 = "cf", "cc1", "cc2"
NOTAS = [(NOTA_CF, "CF"), (NOTA_CC1, "CC 1.er cuatrimestre"), (NOTA_CC2, "CC 2.º cuatrimestre")]


def resumen_por_etapa(registros: Iterable[RegistroNotas]) -> list[tuple[str, str, Resumen]]:
    """``(clave, nombre, resumen)`` de cada etapa, en el orden de la cursada."""
    registros = list(registros)
    return [(clave, nombre, resumir_etapa(registros, clave)) for clave, nombre in ETAPAS]


def resumen_por_grupo(items: Iterable[T], clave: Callable[[T], str],
                      registro: Callable[[T], RegistroNotas], etapa: str) -> list[tuple[str, Resumen]]:
    """Agrupa ``items`` por ``clave`` y resume la ``etapa`` de cada grupo.

    Ordena de mayor a menor porcentaje de desaprobados (a igualdad, por nombre),
    para que arriba queden los grupos que más necesitan atención. Omite los
    grupos sin alumnos en la etapa (pasa en la IFA).
    """
    grupos: dict[str, list[RegistroNotas]] = {}
    for it in items:
        grupos.setdefault(clave(it), []).append(registro(it))
    filas = [(nombre, resumir_etapa(regs, etapa)) for nombre, regs in grupos.items()]
    filas = [(n, r) for n, r in filas if r.total]
    return sorted(filas, key=lambda f: (-f[1].pct_desaprobados, f[0]))


@dataclass
class Histograma:
    """Cantidad de notas por valor entero (``conteos[0]`` = nota 1 ... ``conteos[9]`` = nota 10).

    Una nota con decimales cuenta en su parte entera: 6,5 suma en el 6.
    """

    conteos: list[int] = field(default_factory=lambda: [0] * (NOTA_MAX - NOTA_MIN + 1))
    sin_nota: int = 0
    zona_limite: int = 0          # notas desde ZONA_LIMITE_DESDE hasta antes de NOTA_APROBACION

    @property
    def con_nota(self) -> int:
        return sum(self.conteos)

    def agregar(self, nota: Optional[float]) -> None:
        if nota is None:
            self.sin_nota += 1
            return
        self.conteos[min(int(nota), NOTA_MAX) - NOTA_MIN] += 1
        if ZONA_LIMITE_DESDE <= nota < NOTA_APROBACION:
            self.zona_limite += 1


def nota_de(reg: RegistroNotas, nota: str) -> Optional[float]:
    """CF (manual o calculada) o CC cargada. La CC de un ausente sin nota no cuenta."""
    if nota == NOTA_CF:
        return evaluar(reg).calificacion_final
    c = reg.c1 if nota == NOTA_CC1 else reg.c2
    return c.calificacion


def histograma(registros: Iterable[RegistroNotas], nota: str) -> Histograma:
    """Distribución de la CF o de la CC de un cuatrimestre."""
    h = Histograma()
    for reg in registros:
        h.agregar(nota_de(reg, nota))
    return h


# ---------------------------------------------------------------------------
# Del 1.er al 2.º cuatrimestre
# ---------------------------------------------------------------------------
ESTADOS_CUATRIMESTRE = [Estado.APROBADO, Estado.DESAPROBADO, Estado.AUSENTE, Estado.PENDIENTE]


@dataclass
class Transiciones:
    """Cuántas notas pasaron de cada estado del 1.er cuatrimestre a cada estado del 2.º."""

    conteos: dict[tuple[Estado, Estado], int] = field(default_factory=dict)

    def cantidad(self, en_c1: Estado, en_c2: Estado) -> int:
        return self.conteos.get((en_c1, en_c2), 0)

    def total_fila(self, en_c1: Estado) -> int:
        return sum(self.cantidad(en_c1, e) for e in ESTADOS_CUATRIMESTRE)

    def pct_fila(self, en_c1: Estado, en_c2: Estado) -> float:
        """Porcentaje sobre los que tuvieron ``en_c1`` en el 1.er cuatrimestre."""
        total = self.total_fila(en_c1)
        return 100.0 * self.cantidad(en_c1, en_c2) / total if total else 0.0


def transiciones(registros: Iterable[RegistroNotas]) -> Transiciones:
    t = Transiciones()
    for reg in registros:
        clave = (estado_cuatrimestre(reg.c1), estado_cuatrimestre(reg.c2))
        t.conteos[clave] = t.conteos.get(clave, 0) + 1
    return t


# ---------------------------------------------------------------------------
# Alumnos en riesgo
# ---------------------------------------------------------------------------
@dataclass
class AlumnoEnRiesgo:
    alumno_id: int
    nombre: str
    curso: str
    materias: list[str]               # materias con CF < 7


@dataclass
class Riesgo:
    """``por_cantidad[k]`` = alumnos con k materias con CF < 7; el último índice es "MATERIAS_RIESGO o más"."""

    por_cantidad: list[int]
    en_riesgo: list[AlumnoEnRiesgo]   # ordenados de más a menos materias

    @property
    def total_alumnos(self) -> int:
        return sum(self.por_cantidad)


def riesgo(filas: Iterable, minimo: int = MATERIAS_RIESGO) -> Riesgo:
    """Cuenta, por alumno, las materias con CF < 7 (las que lo mandan a la IFA).

    ``filas`` son objetos con ``alumno_id``, ``nombre_completo``, ``curso.etiqueta``,
    ``materia`` y ``registro``. Solo se cuentan las materias de ``filas`` (el ámbito
    elegido); una materia Pendiente no suma.
    """
    alumnos: dict[int, AlumnoEnRiesgo] = {}
    for f in filas:
        a = alumnos.setdefault(f.alumno_id, AlumnoEnRiesgo(f.alumno_id, f.nombre_completo, f.curso.etiqueta, []))
        if evaluar(f.registro).va_a_ifa:
            a.materias.append(f.materia)
    por_cantidad = [0] * (minimo + 1)
    for a in alumnos.values():
        por_cantidad[min(len(a.materias), minimo)] += 1
    en_riesgo = sorted((a for a in alumnos.values() if len(a.materias) >= minimo),
                       key=lambda a: (-len(a.materias), a.curso, a.nombre))
    return Riesgo(por_cantidad, en_riesgo)
