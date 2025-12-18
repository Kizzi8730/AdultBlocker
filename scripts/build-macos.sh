#!/usr/bin/env zsh
set -euo pipefail

# Build a macOS app bundle with PyInstaller (windowed)
SCRIPT_DIR=${0:a:h}
PROJECT_ROOT=${SCRIPT_DIR:h}
cd "$PROJECT_ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install pyinstaller -r requirements.txt


# Build with custom icon
pyinstaller --windowed --name AdultBlocker --icon icon.icns --add-data "presets:presets" main.py

echo "\nBuilt dist/AdultBlocker.app\n"
