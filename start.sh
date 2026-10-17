#!/usr/bin/env bash
# JobRadar launcher for macOS / Linux
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then PY=python3; elif command -v python >/dev/null 2>&1; then PY=python; else
  echo "Python 3.10 or newer is required: https://www.python.org/downloads/"; exit 1; fi
exec "$PY" run.py "$@"
