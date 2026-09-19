# Sprint Sarthi

Sprint Sarthi is a human-governed AI Scrum Master that converts architecture documents into a traceable, estimated, dependency-aware, Sprint-ready backlog.

## Run With Docker

Install Docker Desktop on Windows/macOS, or Docker Engine with Compose on Ubuntu/Linux:
https://docs.docker.com/get-docker/

Run one command from the project folder:

Ubuntu/Linux/macOS:
```bash
bash run.sh
```

Windows PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Open http://localhost:3000. API health: http://localhost:8000/health.

On EC2, allow inbound TCP ports `3000` and `8000` in the instance security group. If the server has multiple network addresses, set the public address before starting:

```bash
SPRINT_SARTHI_HOST=YOUR_EC2_PUBLIC_IP bash run.sh
```

Stop the containers with:

```bash
docker compose down
```

## Technology

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, SQLAlchemy, SQLite, Alembic
- AI: LangGraph and GPT-4o through VW LLMAAS

## Run From A Downloaded ZIP (Windows)

### 1. Install Required Software

Install these tools before running the project:

- Python 3.11 or newer: https://www.python.org/downloads/
- Node.js 20 or newer: https://nodejs.org/

During Python installation, select **Add Python to PATH**.

### 2. Extract And Install

1. Extract the ZIP file.
2. Open the extracted `Sprint-Sarthi` folder.
3. Double-click `install-local.bat`.

Alternatively, run it from PowerShell:

```powershell
.\install-local.bat
```

This single installer:

- Creates the Python virtual environment.
- Installs all backend Python dependencies.
- Installs pnpm when it is missing.
- Installs all frontend JavaScript dependencies.
- Creates `backend/.env` when it is missing.
- Creates or updates the local SQLite database.

### 3. Configure LLMAAS

Open `backend/.env` and set these values:

```dotenv
LLM_API_KEY=<your-api-key>
LLMAAS_CLIENT_ID=<your-client-id>
LLMAAS_CLIENT_SECRET=<your-client-secret>
```

Do not share or commit this file.

### 4. Start The Application

Open two PowerShell windows in the extracted project folder.

First window:

```powershell
.\start-backend.bat
```

Second window:

```powershell
.\start-frontend.bat
```

### 5. Open In Browser

- Application: http://localhost:3000
- API health: http://127.0.0.1:8000/health
- API documentation: http://127.0.0.1:8000/docs
- Operational logs: http://localhost:3000/logs

Demo login: `admin / password`

## Manual Installation (Fallback)

Backend:

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test,ai]"
Copy-Item .env.example .env
python -m alembic upgrade head
```

Frontend:

```powershell
cd frontend
npm install --global pnpm@10.34.5
pnpm install --frozen-lockfile
```

## Verify Installation

Backend tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

Frontend checks:

```powershell
cd frontend
pnpm lint
pnpm build
```

## Basic Workflow

1. Create a project and upload architecture documents.
2. Process documents and answer clarifications.
3. Generate, enrich, estimate, and analyze the backlog.
4. Upload verified Planning Data.
5. Review assignments, Sprint planning, duplicates, quality, and board health.
6. Record human approval.
7. Publish, preview, and download the Excel workbook.

AI outputs remain proposals. Sprint Sarthi never automatically approves or publishes work.

## Common Issues

- **Python not found:** reinstall Python and enable **Add Python to PATH**.
- **PowerShell activation blocked:** run `Set-ExecutionPolicy -Scope Process Bypass`.
- **Port already in use:** stop the process using port 8000 or 3000.
- **Frontend cannot reach the API:** confirm http://127.0.0.1:8000/health returns `ok`.
- **LLMAAS authentication error:** verify the three credential values in `backend/.env`.