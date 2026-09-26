"""Inicializa la base de datos SQLite (estructura escolar + datos de prueba).

Uso:
    python init_db.py                 # crea la BD si no existe / está vacía
    python init_db.py --reset         # la borra y la vuelve a crear
    python init_db.py --sin-alumnos   # solo la estructura, sin alumnos ni notas
"""
import argparse

from app.config import DB_PATH
from app.data.seed import inicializar

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset", action="store_true", help="recrear todas las tablas")
    ap.add_argument("--alumnos", type=int, default=20, help="alumnos por curso (defecto 20)")
    ap.add_argument("--sin-alumnos", action="store_true", help="no generar alumnos ni notas de prueba")
    args = ap.parse_args()
    inicializar(alumnos_por_curso=args.alumnos, reset=args.reset,
                datos_prueba=not args.sin_alumnos)
    print(f"Base de datos lista en {DB_PATH}")
