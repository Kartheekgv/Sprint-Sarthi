# Sprint Sarthi

Sprint Sarthi is a human-governed AI Scrum Master that converts architecture and requirement documents into a traceable, estimated, dependency-aware, Sprint-ready backlog.

## Technology

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, SQLAlchemy, SQLite, Alembic
- AI orchestration: LangGraph and GPT-4o through VW LLMAAS
- Output: Browser preview and six-sheet Excel workbook

## Local Installation (Windows)

### Requirements

- Python 3.11+
- Node.js 20+
- pnpm 10+
- Valid LLMAAS credentials

### 1. Backend

Open PowerShell in the project folder:

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test,ai]"
Copy-Item .env.example .env
```

This creates `backend/.env` from `backend/.env.example`. Open `backend/.env` and enter your LLMAAS credentials:

```dotenv
LLM_API_KEY=<your-api-key>
LLMAAS_CLIENT_ID=<your-client-id>
LLMAAS_CLIENT_SECRET=<your-client-secret>
```

Create the database and start the API:

```powershell
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend

Open a second PowerShell window in the project folder:

```powershell
cd frontend
pnpm install
$env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8000/api/v1"
pnpm dev
```

### 3. Open The Application

- Application: http://localhost:3000
- API health: http://127.0.0.1:8000/health
- API documentation: http://127.0.0.1:8000/docs
- Operational logs: http://localhost:3000/logs

Demo login: `admin / password`

## Later Runs

Run these scripts in separate PowerShell windows:

```powershell
.\start-backend.bat
.\start-frontend.bat
```

The `backend/.env` file must already contain valid credentials.

## Tests

Backend:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m pytest -q
```

Frontend:

```powershell
cd frontend
pnpm lint
pnpm build
```

## Basic Workflow

1. Create a project and upload architecture documents.
2. Process documents and answer required clarifications.
3. Run the backlog, enrichment, estimation, and dependency agents.
4. Upload verified Planning Data and review assignments and Sprint scope.
5. Run duplicate detection, quality checks, and board health.
6. Record named human approval.
7. Publish, preview, and download the Excel workbook.

AI outputs remain proposals. Sprint Sarthi never automatically approves or publishes work.

## Common Issues

- If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass`.
- If the frontend cannot reach the API, verify the backend health URL and restart `pnpm dev` after setting `NEXT_PUBLIC_API_URL`.
- If port 8000 or 3000 is busy, stop the existing process before restarting.
- A Planning Data response can contain blocking validation issues. Assignment unlocks only after a valid workbook is imported.