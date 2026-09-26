"""Capa de datos - consultas SQL (repositorio).

Devuelve dataclasses simples; NO calcula estados ni notas finales (eso es
responsabilidad de ``app.logic``). Los tipos de retorno usan la lógica solo
para armar :class:`RegistroNotas` a partir de las columnas.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from app.data.database import lectura, transaccion
from app.logic.calificaciones import Cuatrimestre, RegistroNotas

# Orden de las columnas de la tabla `notas` que edita la GUI.
COLUMNAS_NOTAS = (
    "c1_nota1", "c1_nota2", "c1_int", "c1_cal", "c1_ausente",
    "c2_nota1", "c2_nota2", "c2_int", "c2_cal", "c2_ausente",
    "if_nota", "if_ausente", "cf_manual",
)


@dataclass(frozen=True)
class Departamento:
    id: int
    nombre: str
    jefe: str


@dataclass(frozen=True)
class Curso:
    id: int
    anio: int
    division: int
    ciclo: str
    orientacion: Optional[str]

    @property
    def etiqueta(self) -> str:
        """Ej.: ``1°1°`` (ciclo básico) o ``4º5º`` (orientado)."""
        sep = "°" if self.anio <= 3 else "º"
        return f"{self.anio}{sep}{self.division}{sep}"


@dataclass(frozen=True)
class Materia:
    id: int
    nombre: str
    departamento_id: int


@dataclass(frozen=True)
class Alumno:
    id: int
    apellido: str
    nombre: str
    dni: str
    curso_id: int

    @property
    def nombre_completo(self) -> str:
        return f"{self.apellido}, {self.nombre}"


class DniDuplicado(ValueError):
    """Ya existe otro alumno con ese DNI."""


@dataclass
class FilaAlumno:
    """Un alumno con sus notas en una materia."""

    alumno_id: int
    materia_id: int
    apellido: str
    nombre: str
    curso: Curso
    materia: str
    registro: RegistroNotas

    @property
    def nombre_completo(self) -> str:
        return f"{self.apellido}, {self.nombre}"


def _registro_desde_fila(f: sqlite3.Row) -> RegistroNotas:
    """Convierte las columnas de `notas` (posiblemente NULL) en RegistroNotas."""
    def cuat(p: str) -> Cuatrimestre:
        return Cuatrimestre(f[f"{p}_nota1"], f[f"{p}_nota2"], f[f"{p}_int"],
                            f[f"{p}_cal"], bool(f[f"{p}_ausente"] or 0))
    return RegistroNotas(cuat("c1"), cuat("c2"), f["if_nota"], bool(f["if_ausente"] or 0),
                         f["cf_manual"])


def _curso_desde_fila(f: sqlite3.Row) -> Curso:
    return Curso(f["curso_id"], f["anio"], f["division"], f["ciclo"], f["orientacion"])


# ---------------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------------
def listar_departamentos() -> list[Departamento]:
    with lectura() as con:
        return [Departamento(r["id"], r["nombre"], r["jefe"])
                for r in con.execute("SELECT * FROM departamentos ORDER BY id")]


def actualizar_jefe(departamento_id: int, jefe: str) -> None:
    with transaccion() as con:
        con.execute("UPDATE departamentos SET jefe = ? WHERE id = ?", (jefe, departamento_id))


def listar_cursos() -> list[Curso]:
    with lectura() as con:
        return [Curso(r["id"], r["anio"], r["division"], r["ciclo"], r["orientacion"])
                for r in con.execute("SELECT * FROM cursos ORDER BY anio, division")]


def listar_materias_de_curso(curso_id: int) -> list[Materia]:
    with lectura() as con:
        rows = con.execute(
            """SELECT m.* FROM materias m
               JOIN curso_materia cm ON cm.materia_id = m.id
               WHERE cm.curso_id = ? ORDER BY m.nombre""", (curso_id,))
        return [Materia(r["id"], r["nombre"], r["departamento_id"]) for r in rows]


def listar_materias() -> list[Materia]:
    with lectura() as con:
        return [Materia(r["id"], r["nombre"], r["departamento_id"])
                for r in con.execute("SELECT * FROM materias ORDER BY nombre")]


# ---------------------------------------------------------------------------
# Alumnos
# ---------------------------------------------------------------------------
def listar_alumnos(curso_id: int) -> list[Alumno]:
    with lectura() as con:
        return [Alumno(r["id"], r["apellido"], r["nombre"], r["dni"], r["curso_id"])
                for r in con.execute(
                    "SELECT * FROM alumnos WHERE curso_id = ? ORDER BY apellido, nombre",
                    (curso_id,))]


def crear_alumno(apellido: str, nombre: str, dni: str, curso_id: int) -> int:
    """Da de alta un alumno; lanza :class:`DniDuplicado` si el DNI ya existe."""
    try:
        with transaccion() as con:
            cur = con.execute(
                "INSERT INTO alumnos (apellido, nombre, dni, curso_id) VALUES (?, ?, ?, ?)",
                (apellido, nombre, dni, curso_id))
            return cur.lastrowid
    except sqlite3.IntegrityError as e:
        raise DniDuplicado(dni) from e


def actualizar_alumno(alumno_id: int, apellido: str, nombre: str, dni: str, curso_id: int) -> None:
    try:
        with transaccion() as con:
            con.execute(
                "UPDATE alumnos SET apellido = ?, nombre = ?, dni = ?, curso_id = ? WHERE id = ?",
                (apellido, nombre, dni, curso_id, alumno_id))
    except sqlite3.IntegrityError as e:
        raise DniDuplicado(dni) from e


def contar_notas_alumno(alumno_id: int) -> int:
    with lectura() as con:
        return con.execute("SELECT COUNT(*) FROM notas WHERE alumno_id = ?",
                           (alumno_id,)).fetchone()[0]


def eliminar_alumno(alumno_id: int) -> None:
    """Borra el alumno y (por ON DELETE CASCADE) todas sus notas."""
    with transaccion() as con:
        con.execute("DELETE FROM alumnos WHERE id = ?", (alumno_id,))


# ---------------------------------------------------------------------------
# Notas
# ---------------------------------------------------------------------------
_SELECT_FILAS = """
SELECT a.id AS alumno_id, a.apellido, a.nombre, m.id AS materia_id, m.nombre AS materia,
       c.id AS curso_id, c.anio, c.division, c.ciclo, c.orientacion,
       n.c1_nota1, n.c1_nota2, n.c1_int, n.c1_cal, n.c1_ausente,
       n.c2_nota1, n.c2_nota2, n.c2_int, n.c2_cal, n.c2_ausente,
       n.if_nota, n.if_ausente, n.cf_manual
FROM alumnos a
JOIN cursos c         ON c.id = a.curso_id
JOIN curso_materia cm ON cm.curso_id = c.id
JOIN materias m       ON m.id = cm.materia_id
LEFT JOIN notas n     ON n.alumno_id = a.id AND n.materia_id = m.id
"""


def _a_fila_alumno(r: sqlite3.Row) -> FilaAlumno:
    return FilaAlumno(r["alumno_id"], r["materia_id"], r["apellido"], r["nombre"],
                      _curso_desde_fila(r), r["materia"], _registro_desde_fila(r))


def listar_filas(curso_id: Optional[int] = None, materia_id: Optional[int] = None,
                 departamento_id: Optional[int] = None) -> list[FilaAlumno]:
    """Alumnos (con o sin notas cargadas) filtrados por curso/materia/departamento."""
    where, params = [], []
    if curso_id is not None:
        where.append("c.id = ?"); params.append(curso_id)
    if materia_id is not None:
        where.append("m.id = ?"); params.append(materia_id)
    if departamento_id is not None:
        where.append("m.departamento_id = ?"); params.append(departamento_id)
    sql = _SELECT_FILAS + (" WHERE " + " AND ".join(where) if where else "")
    sql += " ORDER BY c.anio, c.division, m.nombre, a.apellido, a.nombre"
    with lectura() as con:
        return [_a_fila_alumno(r) for r in con.execute(sql, params)]


def guardar_notas(alumno_id: int, materia_id: int, valores: dict) -> None:
    """Inserta o actualiza (UPSERT) las notas de un alumno en una materia."""
    guardar_notas_lote([(alumno_id, materia_id, valores)])


def guardar_notas_lote(lote: list[tuple[int, int, dict]]) -> None:
    """Guarda muchas filas en una sola transacción.

    ``valores`` es un dict con claves de :data:`COLUMNAS_NOTAS`.
    """
    cols = ", ".join(COLUMNAS_NOTAS)
    marcas = ", ".join("?" * len(COLUMNAS_NOTAS))
    sets = ", ".join(f"{c} = excluded.{c}" for c in COLUMNAS_NOTAS)
    sql = (f"INSERT INTO notas (alumno_id, materia_id, {cols}) VALUES (?, ?, {marcas}) "
           f"ON CONFLICT(alumno_id, materia_id) DO UPDATE SET {sets}")
    with transaccion() as con:
        con.executemany(sql, [
            (a, m, *[v.get(c) if not c.endswith("ausente") else int(bool(v.get(c)))
                     for c in COLUMNAS_NOTAS])
            for a, m, v in lote
        ])


# ---------------------------------------------------------------------------
# Textos cualitativos del informe
# ---------------------------------------------------------------------------
def cargar_textos_informe(departamento_id: int) -> dict[str, str]:
    with lectura() as con:
        return {r["clave"]: r["valor"] for r in con.execute(
            "SELECT clave, valor FROM informe_textos WHERE departamento_id = ?",
            (departamento_id,))}


def guardar_textos_informe(departamento_id: int, textos: dict[str, str]) -> None:
    with transaccion() as con:
        con.executemany(
            """INSERT INTO informe_textos (departamento_id, clave, valor) VALUES (?, ?, ?)
               ON CONFLICT(departamento_id, clave) DO UPDATE SET valor = excluded.valor""",
            [(departamento_id, k, v) for k, v in textos.items()])
