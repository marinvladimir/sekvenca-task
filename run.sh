#!/usr/bin/env bash
# Pokreće Kadar web aplikaciju (http://127.0.0.1:8770). Prvo jednom pokreni ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Prvo pokreni ./setup.sh"; exit 1; }
exec .venv/bin/python -m kadar app "$@"
