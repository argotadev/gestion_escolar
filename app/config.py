"""Configuración global de la aplicación (rutas y constantes de negocio).

Rutas
-----
* En desarrollo (``python main.py``) todo vive junto al código.
* Empaquetada como ``.exe`` (PyInstaller / ``flet pack``) el código se
  descomprime en una carpeta temporal de solo lectura (``sys._MEIPASS``), por
  eso los datos del usuario (base de datos e informes) se guardan en la carpeta
  de datos del usuario (en Windows ``%LOCALAPPDATA%\\GestionNotas``). Así no se
  pierden aunque el .exe se abra directamente desde el .zip (Windows lo extrae a
  una carpeta temporal que después borra), esté en una carpeta sin permisos de
  escritura o se descargue una versión nueva en otro lugar.
* Modo portátil: si ya hay un ``escuela.db`` junto al ejecutable (las versiones
  anteriores lo creaban allí) se sigue usando ese, salvo que el .exe esté en una
  carpeta temporal.
* La plantilla ``informe.docx`` se busca primero junto al ejecutable (para que se
  pueda reemplazar) y, si no está, se usa la copia incluida en el paquete.
"""
import os
import sys
import tempfile
from pathlib import Path

APP_NOMBRE = "GestionNotas"
EMPAQUETADO = bool(getattr(sys, "frozen", False))


def _carpeta_datos_usuario() -> Path:
    """Carpeta estándar del sistema para los datos de la aplicación."""
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / APP_NOMBRE


def _es_temporal(carpeta: Path) -> bool:
    return carpeta.is_relative_to(Path(tempfile.gettempdir()).resolve())


if EMPAQUETADO:
    BASE_DIR = Path(sys.executable).resolve().parent               # carpeta del .exe
    RECURSOS_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))       # archivos incluidos
    portatil = (BASE_DIR / "escuela.db").exists() and not _es_temporal(BASE_DIR)
    DATOS_DIR = BASE_DIR if portatil else _carpeta_datos_usuario()
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    RECURSOS_DIR = DATOS_DIR = BASE_DIR

DB_PATH = DATOS_DIR / "escuela.db"
OUTPUT_DIR = DATOS_DIR / "informes_generados"


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
