@echo off
setlocal
cd /d "%~dp0"

echo [1/6] Checking Python 3.11...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer is required.
  echo Download it from https://www.python.org/downloads/
  exit /b 1
)

echo [2/6] Checking Node.js 20...
node --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js 20 or newer is required.
  echo Download it from https://nodejs.org/
  exit /b 1
)

echo [3/6] Installing pnpm when needed...
where pnpm >nul 2>&1
if errorlevel 1 (
  call npm install --global pnpm@10.34.5
  if errorlevel 1 exit /b 1
)

echo [4/6] Installing backend dependencies...
pushd backend
if not exist ".venv\Scripts\python.exe" py -3.11 -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -e ".[test,ai]"
if errorlevel 1 exit /b 1
if not exist ".env" copy ".env.example" ".env" >nul
.venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 exit /b 1
popd

echo [5/6] Installing frontend dependencies...
pushd frontend
call pnpm install --frozen-lockfile
if errorlevel 1 exit /b 1
popd

echo [6/6] Installation complete.
echo.
echo Edit backend\.env with valid LLMAAS credentials.
echo Then run start-backend.bat and start-frontend.bat in separate terminals.
endlocal
