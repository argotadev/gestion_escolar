"""Creación y carga inicial (datos semilla) de la base de datos."""
from __future__ import annotations

import random
import sqlite3

from app.config import NOTA_APROBACION, NOTA_AUSENTE
from app.data import estructura_escolar as est
from app.data.database import conectar, crear_esquema

APELLIDOS = [
    "González", "Rodríguez", "Gómez", "Fernández", "López", "Díaz", "Martínez",
    "Pérez", "Romero", "Sánchez", "García", "Sosa", "Álvarez", "Torres", "Ruiz",
    "Ramírez", "Flores", "Acosta", "Benítez", "Medina", "Herrera", "Suárez",
    "Aguirre", "Giménez", "Gutiérrez", "Peralta", "Cabrera", "Ríos", "Ojeda",
]
NOMBRES = [
    "Mateo", "Valentina", "Santiago", "Sofía", "Benjamín", "Martina", "Thiago",
    "Camila", "Lucas", "Milagros", "Joaquín", "Lucía", "Nicolás", "Agustina",
    "Franco", "Julieta", "Tomás", "Florencia", "Bruno", "Abril", "Ezequiel",
    "Micaela", "Facundo", "Brisa", "Lautaro", "Rocío", "Gonzalo", "Candela",
]


def _poblar_estructura(con: sqlite3.Connection) -> None:
    """Departamentos, cursos, materias y su asignación a cada curso."""
    for nombre, jefe in est.DEPARTAMENTOS.items():
        con.execute("INSERT INTO departamentos (nombre, jefe) VALUES (?, ?)", (nombre, jefe))
    dep_id = {r["nombre"]: r["id"] for r in con.execute("SELECT * FROM departamentos")}

    for materia, dep in est.MATERIA_DEPARTAMENTO.items():
        con.execute("INSERT INTO materias (nombre, departamento_id) VALUES (?, ?)",
                    (materia, dep_id[dep]))
    mat_id = {r["nombre"]: r["id"] for r in con.execute("SELECT * FROM materias")}

    def crear_curso(anio, division, ciclo, orientacion, materias):
        cur = con.execute(
            "INSERT INTO cursos (anio, division, ciclo, orientacion) VALUES (?,?,?,?)",
            (anio, division, ciclo, orientacion))
        con.executemany("INSERT INTO curso_materia (curso_id, materia_id) VALUES (?,?)",
                        [(cur.lastrowid, mat_id[m]) for m in materias])

    for anio, materias in est.MATERIAS_BASICO.items():
        for div in est.DIVISIONES_BASICO:
            crear_curso(anio, div, "BASICO", None, materias)
    for (anio, orient), materias in est.MATERIAS_ORIENTADO.items():
        for div in est.ORIENTACIONES[orient]:
            crear_curso(anio, div, "ORIENTADO", orient, materias)


def _nota_mock(rng: random.Random) -> dict:
    """Genera un registro de notas verosímil (con ausentes, IFA, pendientes)."""
    def cuat(prefijo: str, pendiente: bool = False) -> dict:
        if pendiente:
            return {}
        if rng.random() < 0.05:                        # ausente: notas vacías (=4)
            return {f"{prefijo}_ausente": 1}
        n1, n2 = rng.choice([5, 6, 6, 7, 7, 8, 8, 9, 10, 3, 4]), rng.choice([5, 6, 7, 7, 8, 9, 10, 4])
        d = {f"{prefijo}_nota1": n1, f"{prefijo}_nota2": n2}
        if min(n1, n2) < 6:                            # intensificación cuatrimestral
            it = rng.choice([4, 5, 6, 6, 7, 8])
            d[f"{prefijo}_int"] = it
            d[f"{prefijo}_cal"] = it if it >= 6 else min(5, max(it, min(n1, n2)))
        else:
            d[f"{prefijo}_cal"] = (n1 + n2) // 2
        return d

    d = {}
    d.update(cuat("c1"))
    d.update(cuat("c2", pendiente=rng.random() < 0.03))
    # Misma regla que app.logic: ausente con CC vacía = 4; va a IFA si CF < 7.
    cc = [d.get(f"{p}_cal", NOTA_AUSENTE if d.get(f"{p}_ausente") else None) for p in ("c1", "c2")]
    van_a_ifa = None not in cc and (cc[0] + cc[1]) / 2 < NOTA_APROBACION
    if van_a_ifa and rng.random() < 0.8:                 # 80 % ya rindió la IFA
        if rng.random() < 0.08:
            d["if_ausente"] = 1                         # no se presentó
        else:
            d["if_nota"] = rng.choice([3, 4, 5, 6, 6, 7, 7, 8, 9])
    return d


def _poblar_alumnos_y_notas(con: sqlite3.Connection, alumnos_por_curso: int, rng: random.Random) -> None:
    dnis: set[str] = set()
    columnas = ["c1_nota1", "c1_nota2", "c1_int", "c1_cal", "c1_ausente",
                "c2_nota1", "c2_nota2", "c2_int", "c2_cal", "c2_ausente",
                "if_nota", "if_ausente"]
    for curso in con.execute("SELECT id FROM cursos").fetchall():
        materias = [r["materia_id"] for r in con.execute(
            "SELECT materia_id FROM curso_materia WHERE curso_id = ?", (curso["id"],))]
        for _ in range(alumnos_por_curso):
            while True:
                dni = str(rng.randint(40_000_000, 50_000_000))
                if dni not in dnis:
                    dnis.add(dni)
                    break
            cur = con.execute(
                "INSERT INTO alumnos (apellido, nombre, dni, curso_id) VALUES (?,?,?,?)",
                (rng.choice(APELLIDOS), rng.choice(NOMBRES), dni, curso["id"]))
            filas = []
            for mid in materias:
                n = _nota_mock(rng)
                filas.append((cur.lastrowid, mid, *[n.get(c) if not c.endswith("ausente") else n.get(c, 0)
                                                    for c in columnas]))
            con.executemany(
                f"INSERT INTO notas (alumno_id, materia_id, {', '.join(columnas)}) "
                f"VALUES (?, ?, {', '.join('?' * len(columnas))})", filas)


def inicializar(alumnos_por_curso: int = 20, semilla: int = 2026, reset: bool = False,
                datos_prueba: bool = False) -> None:
    """Crea el esquema y, si la base está vacía, carga la estructura escolar.

    :param reset: si es True borra todas las tablas antes de recrearlas.
    :param datos_prueba: si es True además genera alumnos y notas al azar.
    """
    con = conectar()
    try:
        if reset:
            for t in ("informe_textos", "notas", "alumnos", "curso_materia",
                      "materias", "cursos", "departamentos"):
                con.execute(f"DROP TABLE IF EXISTS {t}")
        crear_esquema(con)
        if con.execute("SELECT COUNT(*) FROM departamentos").fetchone()[0] == 0:
            rng = random.Random(semilla)            # semilla fija = datos reproducibles
            _poblar_estructura(con)
            if datos_prueba:
                _poblar_alumnos_y_notas(con, alumnos_por_curso, rng)
        con.commit()
    finally:
        con.close()
