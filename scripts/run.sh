#!/usr/bin/env zsh
set -euo pipefail

# Run the app using the project venv Python, avoiding system Python.
SCRIPT_DIR=${0:a:h}
PROJECT_ROOT=${SCRIPT_DIR:h}
cd "$PROJECT_ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
"$VIRTUAL_ENV/bin/python" main.py
