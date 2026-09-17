@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -e ".[ai]"
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
