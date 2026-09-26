# Gestión de Notas e Informes – Escuela Secundaria

Aplicación de escritorio local: **Python + Flet (interfaz) + SQLite + python-docx**.

## Ejecutar en desarrollo (Linux / Windows / macOS)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py            # la primera vez crea escuela.db con datos de prueba
python init_db.py --reset # (opcional) recrea la base con datos semilla
python -m unittest discover -s tests -v   # pruebas de las reglas de negocio
```

## Generar el .exe (en Windows)
1. Instalar Python 3.10+ (python.org, marcando *Add Python to PATH*).
2. Copiar la carpeta del proyecto a Windows y ejecutar **`build_windows.bat`** (doble clic).
   * Resultado: `dist\GestionNotas.exe` (un solo archivo).
   * `build_windows.bat onedir` genera una carpeta `dist\GestionNotas\` (arranca más rápido
     y suele dar menos falsos positivos de antivirus).
3. Copiar el `.exe` (o la carpeta) a cualquier lugar **con permisos de escritura**
   (no `Program Files`): junto a él se crean `escuela.db` y `informes_generados\`.

Notas:
* `informe.docx` viaja dentro del .exe. Si se coloca un `informe.docx` **junto al .exe**, se usa ese
  (permite actualizar la plantilla sin recompilar).
* Un .exe sin firma digital puede mostrar el aviso de SmartScreen ("Más información → Ejecutar de todas formas")
  o ser marcado por el antivirus; es normal en ejecutables generados con PyInstaller.
* El .exe solo se puede compilar en Windows (no es posible cruzar-compilar desde Linux).
  `build_linux.sh` genera un binario Linux con el mismo mecanismo, útil para probar.

## Arquitectura
| Capa | Carpeta | Contenido |
|---|---|---|
| Datos | `app/data` | esquema SQLite, consultas (`repository.py`), estructura escolar y seed |
| Lógica | `app/logic` | `calificaciones.py` (reglas de notas y CF), `estadisticas.py` (agregados) |
| Informes | `app/reports` | `informe_docx.py` completa la plantilla Word |
| Presentación | `app/ui` | tema (`tema.py`), 3 vistas Flet y ventana principal |

Rutas (`app/config.py`): en desarrollo todo vive junto al código; empaquetado, los datos del usuario
van junto al .exe y los recursos incluidos se leen de la carpeta temporal de PyInstaller.

## Reglas implementadas (`app/logic/calificaciones.py`)
* Nota de aprobación **7** (`NOTA_APROBACION` en `app/config.py`).
* Cuatrimestre = Nota 1 + Nota 2 (+ Intensificación cuatrimestral) → **Calificación del cuatrimestre** cargada a mano (no es promedio).
* **Ausente**: nota 4 por defecto, pasa directo a IF; si se presenta y aprueba, aprueba la materia.
* **IF**: van los que no aprobaron ambos cuatrimestres o estuvieron ausentes. `CF = nota de la IF`.
* **Flujo normal**: `CF = (Cal1 + Cal2) / 2` (promedio exacto).
* La CF es la única nota con decimales (hasta 2): el valor calculado se propone y el docente puede corregirlo a mano. Aprueba si CF ≥ 7.

## Supuestos a confirmar
* Informe, categorías excluyentes: **Aprobados** (por promedio o IF), **Ausentes** (ausente que aún no rindió la IF),
  **Desaprobados** (desaprobó, debe IF sin ser ausente, o ausente que no aprobó/no rindió la IF).
  Los registros "Pendiente" cuentan en el total pero en ninguna columna.
* El informe se guarda automáticamente en `informes_generados/` (con opción de abrirlo o abrir la carpeta).
* Ubicación de TIC, EDI y seminarios en departamentos: ver `app/data/estructura_escolar.py`.
