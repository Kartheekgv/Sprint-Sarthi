# Sprint Sarthi

Sprint Sarthi is a local web application with a FastAPI backend and a Next.js frontend.

## Windows Setup With Docker

### 1. Install the prerequisites manually

Install these applications yourself:

- Git: https://git-scm.com/download/win
- Docker Desktop: https://www.docker.com/products/docker-desktop/

Start Docker Desktop and wait until it says Docker is running.

### 2. Download the project

Open PowerShell and run:

```powershell
git clone https://github.com/Kartheekgv/Sprint-Sarthi.git
cd Sprint-Sarthi
```

If the project is already downloaded:

```powershell
cd path\to\Sprint-Sarthi
git pull origin main
```

### 3. Configure optional AI access

The application starts without an environment file. To configure LLMAAS, copy the example file:

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Set the required credentials in `backend\.env`. Do not commit or share that file.

### 4. Start the application

Run this command from the project folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

This command only checks that Docker is installed and running, then builds and starts the containers. It does not install Docker, modify Windows, or modify AWS.

### 5. Open the application

- UI: http://localhost:3000
- API through the UI: http://localhost:3000/api/v1
- Health check: http://localhost:3000/health

The backend is private to Docker and is intentionally not exposed as a separate public port.

### 6. Stop the application

```powershell
docker compose down
```

View logs:

```powershell
docker compose logs -f
```

## Manual Installation Without Docker

Use this option only when you do not want Docker. Install Python 3.11 or newer and Node.js 20 or newer first:

- Python: https://www.python.org/downloads/
- Node.js: https://nodejs.org/

### Backend

Open PowerShell in the project folder:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
Copy-Item .env.example .env
python -m alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

Open a second PowerShell window:

```powershell
cd path\to\Sprint-Sarthi\frontend
corepack enable
corepack prepare pnpm@10.34.5 --activate
pnpm install --frozen-lockfile
$env:BACKEND_INTERNAL_URL = "http://127.0.0.1:8000"
pnpm dev
```

Open http://localhost:3000.

## Verification

From the project folder:

```powershell
docker compose config
docker compose ps
Invoke-WebRequest http://localhost:3000/health
```

## Tests

Backend tests:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

Frontend checks:

```powershell
cd frontend
pnpm lint
pnpm build
```

## Technology

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, SQLAlchemy, SQLite, Alembic
- AI: LangGraph and LLMAAS/OpenAI-compatible APIs
