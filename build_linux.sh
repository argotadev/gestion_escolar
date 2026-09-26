#!/usr/bin/env bash
# Genera un binario para Linux (sirve para probar el empaquetado antes de ir a Windows).
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt -r requirements-build.txt
rm -rf build dist
flet pack main.py --name GestionNotas --add-data "informe.docx:." -y
echo "Listo: dist/GestionNotas"
