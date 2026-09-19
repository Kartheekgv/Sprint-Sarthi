# Sprint Sarthi

Sprint Sarthi runs locally on Windows with Python and Node.js. Docker, Docker Desktop, AWS, WSL, and administrator permissions are not required.

## Windows Setup

### 1. Install prerequisites

Install these manually before starting:

- Git: https://git-scm.com/download/win
- Python 3.11 or newer: https://www.python.org/downloads/
- Node.js 20 or newer: https://nodejs.org/

During Python installation, enable **Add Python to PATH**.

Verify the installations in PowerShell:

```powershell
py --version
node --version
npx --version
```

Python 3.11 or newer and Node.js 20 or newer are required.

### 2. Download the project

Open PowerShell:

```powershell
git clone https://github.com/Kartheekgv/Sprint-Sarthi.git
cd Sprint-Sarthi
```

For an existing checkout:

```powershell
cd path\to\Sprint-Sarthi
git pull origin main
```

### 3. Install the project

Run from the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-local.ps1
```

This creates `backend\.venv`, installs Python and frontend dependencies, creates `backend\.env`, and runs database migrations. It does not install global packages or modify AWS.

### 4. Configure optional AI access

Open the local environment file:

```powershell
notepad backend\.env
```

Add your LLMAAS credentials if AI features are needed. Do not commit or share this file.

The application can start without AI credentials, but AI workflow features will require valid values in `backend\.env`.

### 5. Start the backend

Open PowerShell window 1:

```powershell
cd path\to\Sprint-Sarthi
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
```

Leave this window running. The backend listens on `http://127.0.0.1:8000`.

### 6. Start the frontend

Open PowerShell window 2:

```powershell
cd path\to\Sprint-Sarthi
powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1
```

Leave this window running. The frontend listens on `http://localhost:3000`.

### 7. Open the application

- UI: http://localhost:3000
- Health check: http://localhost:3000/health
- API documentation: http://localhost:3000/api/v1/docs

Open the UI in your browser at **http://localhost:3000**.

Demo login:

```text
Username: admin
Password: password
```

Keep both PowerShell windows running while using the application. Press `Ctrl+C` in each window to stop it.

### Verify the running application

From a third PowerShell window:

```powershell
Invoke-WebRequest http://localhost:3000/health
Invoke-WebRequest http://localhost:3000/api/v1/projects
```

Both requests should return HTTP `200`.

### Troubleshooting

- If `py` is not recognized, reinstall Python and enable **Add Python to PATH**.
- If scripts are blocked, use the `powershell -ExecutionPolicy Bypass -File ...` commands shown above.
- If the UI does not load, confirm both backend and frontend PowerShell windows are still running.
- If port `3000` or `8000` is busy, stop the process using it before starting Sprint Sarthi.

## Tests

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
cd frontend
npx --yes pnpm@10.34.5 lint
npx --yes pnpm@10.34.5 build
```

## Technology

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, SQLAlchemy, SQLite, Alembic
- AI: LangGraph and LLMAAS/OpenAI-compatible APIs
