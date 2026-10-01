"""Capa de datos - conexión y esquema SQLite.

Solo define cómo se guarda la información; ninguna regla de negocio vive aquí.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import DB_PATH

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departamentos (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    jefe   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS cursos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anio        INTEGER NOT NULL CHECK (anio BETWEEN 1 AND 6),
    division    INTEGER NOT NULL CHECK (division BETWEEN 1 AND 10),
    ciclo       TEXT NOT NULL CHECK (ciclo IN ('BASICO', 'ORIENTADO')),
    orientacion TEXT,                     -- NULL en ciclo básico
    UNIQUE (anio, division)
);

CREATE TABLE IF NOT EXISTS materias (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL UNIQUE,
    departamento_id INTEGER NOT NULL REFERENCES departamentos(id)
);

-- Qué materias se dictan en qué curso (un curso tiene muchas materias).
CREATE TABLE IF NOT EXISTS curso_materia (
    curso_id   INTEGER NOT NULL REFERENCES cursos(id)   ON DELETE CASCADE,
    materia_id INTEGER NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
    PRIMARY KEY (curso_id, materia_id)
);

CREATE TABLE IF NOT EXISTS alumnos (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    apellido TEXT NOT NULL,
    nombre   TEXT NOT NULL,
    dni      TEXT NOT NULL UNIQUE,
    curso_id INTEGER NOT NULL REFERENCES cursos(id)
);

-- Una fila por (alumno, materia) con TODAS las instancias del ciclo lectivo.
-- cN_cal = "Calificación del cuatrimestre": nota definitiva de cierre de etapa,
-- cargada a mano (NO se deriva de las notas previas).
CREATE TABLE IF NOT EXISTS notas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    alumno_id   INTEGER NOT NULL REFERENCES alumnos(id)  ON DELETE CASCADE,
    materia_id  INTEGER NOT NULL REFERENCES materias(id) ON DELETE CASCADE,

    c1_nota1    INTEGER CHECK (c1_nota1 BETWEEN 1 AND 10),
    c1_nota2    INTEGER CHECK (c1_nota2 BETWEEN 1 AND 10),
    c1_int      INTEGER CHECK (c1_int   BETWEEN 1 AND 10),
    c1_cal      INTEGER CHECK (c1_cal   BETWEEN 1 AND 10),
    c1_ausente  INTEGER NOT NULL DEFAULT 0,

    c2_nota1    INTEGER CHECK (c2_nota1 BETWEEN 1 AND 10),
    c2_nota2    INTEGER CHECK (c2_nota2 BETWEEN 1 AND 10),
    c2_int      INTEGER CHECK (c2_int   BETWEEN 1 AND 10),
    c2_cal      INTEGER CHECK (c2_cal   BETWEEN 1 AND 10),
    c2_ausente  INTEGER NOT NULL DEFAULT 0,

    if_nota     INTEGER CHECK (if_nota BETWEEN 1 AND 10),
    if_ausente  INTEGER NOT NULL DEFAULT 0,   -- no se presentó a la IFA
    cf_manual   REAL CHECK (cf_manual BETWEEN 1 AND 10),  -- CF corregida a mano (NULL = calculada)

    UNIQUE (alumno_id, materia_id)
);

-- Textos cualitativos del informe departamental (se recuerdan entre sesiones).
CREATE TABLE IF NOT EXISTS informe_textos (
    departamento_id INTEGER NOT NULL REFERENCES departamentos(id) ON DELETE CASCADE,
    clave           TEXT NOT NULL,
    valor           TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (departamento_id, clave)
);

CREATE INDEX IF NOT EXISTS idx_alumnos_curso ON alumnos(curso_id);
CREATE INDEX IF NOT EXISTS idx_notas_materia ON notas(materia_id);
"""


def conectar(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Abre una conexión con filas accesibles por nombre y FK activadas."""
    con = sqlite3.connect(str(db_path or DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def lectura(db_path: Path | str | None = None):
    """Context manager de solo lectura: abre la conexión y SIEMPRE la cierra."""
    con = conectar(db_path)
    try:
        yield con
    finally:
        con.close()


@contextmanager
def transaccion(db_path: Path | str | None = None):
    """Context manager: abre conexión, hace commit al salir o rollback si falla."""
    con = conectar(db_path)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def crear_esquema(con: sqlite3.Connection) -> None:
    """Crea todas las tablas si aún no existen y migra bases anteriores."""
    con.executescript(SCHEMA)
    columnas = {r["name"] for r in con.execute("PRAGMA table_info(notas)")}
    if "cf_manual" not in columnas:
        con.execute("ALTER TABLE notas ADD COLUMN cf_manual REAL "
                    "CHECK (cf_manual BETWEEN 1 AND 10)")
