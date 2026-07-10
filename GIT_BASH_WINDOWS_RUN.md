# Run Sprint Sarthi on Windows Git Bash

Use this file when you are running the project from Git Bash on a Windows machine.

## Recommended command

Open Git Bash in the project root and run:

```bash
bash run-dev-gitbash.sh
```

This one command does all setup and starts both servers:

1. Creates `.venv`
2. Uses `.venv/Scripts/python.exe` automatically on Windows
3. Installs backend dependencies
4. Creates `.env` from `.env.example`
5. Creates `frontend/.env` from `frontend/.env.example`
6. Ingests the RAG knowledge base
7. Runs `npm install`
8. Starts FastAPI backend
9. Starts React/Vite frontend

## URLs

Backend API docs:

```text
http://127.0.0.1:8000/docs
```

Frontend:

```text
http://localhost:5173
```

## Faster restart after first setup

```bash
bash run-dev-gitbash.sh --skip-install --no-ingest
```

## Setup only

```bash
bash run-dev-gitbash.sh --setup-only
```

## Backend only

```bash
bash run-dev-gitbash.sh --backend-only
```

## Frontend only

```bash
bash run-dev-gitbash.sh --frontend-only
```

## Stop the servers

Press:

```text
Ctrl+C
```

The runner will stop both backend and frontend processes.

## Important note

On Windows Git Bash, the activation path is:

```bash
source .venv/Scripts/activate
```

However, the new runner does not require manual activation. It directly uses the correct virtual environment Python path.

## If ChromaDB fails to install

The runner first tries the full `requirements.txt`. If that fails, it automatically tries `requirements-lite.txt`. The application still works because the RAG layer has a JSON fallback retriever.
