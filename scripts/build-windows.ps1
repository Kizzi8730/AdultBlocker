# Build a Windows executable with PyInstaller (no console)
param()

$ErrorActionPreference = 'Stop'

$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT_ROOT

python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install pyinstaller -r requirements.txt

pyinstaller --noconsole --name AdultBlocker --add-data "presets;presets" main.py

Write-Host "`nBuilt dist/AdultBlocker.exe`n"