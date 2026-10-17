@echo off
title JobRadar
cd /d "%~dp0"
set "PY="
py -3 -c "import sys" 1>NUL 2>NUL && set "PY=py -3"
if not defined PY python -c "import sys" 1>NUL 2>NUL && set "PY=python"
if not defined PY (
  echo Python 3.10 or newer is required.
  echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH" during setup.
  pause
  exit /b 1
)
%PY% run.py %*
if errorlevel 1 pause
