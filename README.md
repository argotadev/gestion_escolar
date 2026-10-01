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
* Cuatrimestre = N1 + N2 (+ **IFC**, Intensificación Cuatrimestral) → **CC** (Calificación Cuatrimestral)
  cargada a mano (no es promedio). La IFC solo se avisa en la grilla; no entra en ningún cálculo.
* Estado de cada cuatrimestre: **Ausente** (Aus. marcado, aunque tenga CC), **Aprobado** (CC ≥ 7),
  **Desaprobado** (CC < 7) o **Pendiente** (CC vacía).
* **CF** = `(CC1 + CC2) / 2` (promedio exacto, también si da menos de 7). Un cuatrimestre con Aus. y CC vacía
  cuenta 4. La CF decide el estado final: **Aprobado** (CF ≥ 7), **Desaprobado** (CF < 7) o **Pendiente** (falta una CC).
* **IFA** (Intensificación Anual): etapa posterior e independiente. Van solo los que tienen CF < 7. Su nota se registra
  (va a otro informe) pero no cambia la CF ni el estado final.
* **Ausente** (estado final): Aus. con CC vacía en los dos cuatrimestres y Aus. marcado en la IFA. Hasta que se marca
  el Aus. de la IFA, figura Desaprobado (CF 4).
* La CF es la única nota con decimales (hasta 2): el valor calculado se propone y el docente puede corregirlo a mano. Aprueba si CF ≥ 7.

## Supuestos a confirmar
* Informe, categorías excluyentes según el estado final (CF): **Aprobados**, **Desaprobados** y **Ausentes**.
  Los registros "Pendiente" cuentan en el total pero en ninguna columna.
* Consolidado: filtro por etapa (Final, 1.er cuatrimestre, 2.º cuatrimestre, IFA) con Total, Aprobados, Desaprobados,
  Ausentes y Pendientes en valor y %. La etapa Final cuenta igual que el informe; la etapa IFA cuenta solo a los
  alumnos con CF < 7. En las etapas cuatrimestrales, la pastilla "Va a IFA" marca a quien tiene CF < 7.
* Análisis (`app/logic/analisis.py`, `app/ui/vista_analisis.py`): gráficos por curso, departamento o toda la escuela,
  sin efecto sobre el informe. La cursada etapa por etapa (barras al 100 %), comparación por materia, curso o
  departamento (ordenada por % de desaprobados) y distribución de notas (CF o CC) con la **zona límite** de 6 a 6,99
  (`ZONA_LIMITE_DESDE` en `app/config.py`), qué pasó del 1.er al 2.º cuatrimestre (tabla de estados, cada fila
  suma 100 %) y alumnos en riesgo: los que tienen `MATERIAS_RIESGO` (3) o más materias con CF < 7, contando solo
  las materias del ámbito elegido. Los gráficos se dibujan con controles de Flet, sin dependencias extra.
* El informe se guarda automáticamente en `informes_generados/` (con opción de abrirlo o abrir la carpeta).
* Ubicación de TIC, EDI y seminarios en departamentos: ver `app/data/estructura_escolar.py`.
