"""Configuración global de la aplicación (rutas y constantes de negocio).

Rutas
-----
* En desarrollo (``python main.py``) todo vive junto al código.
* Empaquetada como ``.exe`` (PyInstaller / ``flet pack``) el código se
  descomprime en una carpeta temporal de solo lectura (``sys._MEIPASS``), por
  eso los datos del usuario (base de datos e informes) se guardan **junto al
  ejecutable**, y la plantilla ``informe.docx`` se busca primero allí (para que
  se pueda reemplazar) y, si no está, se usa la copia incluida en el paquete.
"""
import sys
from pathlib import Path

EMPAQUETADO = bool(getattr(sys, "frozen", False))

if EMPAQUETADO:
    BASE_DIR = Path(sys.executable).resolve().parent               # carpeta del .exe
    RECURSOS_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))       # archivos incluidos
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    RECURSOS_DIR = BASE_DIR

DB_PATH = BASE_DIR / "escuela.db"
OUTPUT_DIR = BASE_DIR / "informes_generados"


def _ruta_plantilla() -> Path:
    junto_al_exe = BASE_DIR / "informe.docx"
    return junto_al_exe if junto_al_exe.exists() else RECURSOS_DIR / "informe.docx"


TEMPLATE_PATH = _ruta_plantilla()

# ---- Constantes de negocio -------------------------------------------------
NOTA_MIN = 1            # Menor nota admitida
NOTA_MAX = 10           # Mayor nota admitida
NOTA_APROBACION = 7     # Nota mínima para aprobar (ajustar según normativa)
NOTA_AUSENTE = 4        # Nota por defecto de todo alumno "Ausente"
ZONA_LIMITE_DESDE = 6   # Zona límite: notas desde 6 hasta antes de NOTA_APROBACION (6 a 6,99)
MATERIAS_RIESGO = 3     # Alumno "en riesgo": esta cantidad o más de materias con CF < NOTA_APROBACION
