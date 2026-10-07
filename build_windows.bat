@echo off
REM ==========================================================================
REM  Genera GestionNotas.exe  (ejecutar en Windows, con doble clic o desde cmd)
REM  Uso:   build_windows.bat            -> un unico .exe  (dist\GestionNotas.exe)
REM         build_windows.bat onedir     -> carpeta con el .exe (arranca mas rapido)
REM ==========================================================================
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instale Python 3.10 o superior desde python.org
    echo y marque "Add Python to PATH" durante la instalacion.
    pause & exit /b 1
)

if not exist .venv (
    echo Creando entorno virtual...
    py -3 -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat

echo Instalando dependencias...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt -r requirements-build.txt || goto :error

if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

set MODO=
if /i "%1"=="onedir" set MODO=--onedir

echo Compilando...
flet pack main.py --name GestionNotas %MODO% ^
    --add-data "informe.docx;." ^
    --product-name "Gestion de Notas e Informes" ^
    --file-description "Gestion de notas e informes escolares" ^
    --product-version 1.0.0 -y || goto :error

echo.
echo ================= LISTO =================
if /i "%1"=="onedir" (
    echo Ejecutable: dist\GestionNotas\GestionNotas.exe
) else (
    echo Ejecutable: dist\GestionNotas.exe
)
echo Los datos se guardan en %LOCALAPPDATA%\GestionNotas (o junto al .exe si alli hay un escuela.db).
pause
exit /b 0

:error
echo.
echo *** Fallo la compilacion. Revise los mensajes de arriba. ***
pause
exit /b 1
