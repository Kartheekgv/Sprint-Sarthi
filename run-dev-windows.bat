@echo off
setlocal
cd /d "%~dp0"
python run_dev.py %*
if errorlevel 1 (
  py -3 run_dev.py %*
)
