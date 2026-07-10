# Sprint Sarthi

Sprint Sarthi is an end-to-end AI-powered Agile planning assistant. It converts messy requirements into clarified requirements, structured backlog, story point estimates, sprint plan, Jira dry run, and Jira ticket creation.

The core design is clarification-first: the AI asks questions instead of guessing missing details.

## Features

- React frontend with requirement input, file upload, clarification screen, backlog cards, sprint plan, and Jira dry run.
- FastAPI backend with clean JSON endpoints.
- Multi-agent architecture: Supervisor, Requirement Gathering, Scope Guardrail, RAG, Backlog, Estimation, Sprint Planner, and Jira agents.
- ChromaDB RAG using local knowledge base documents and deterministic hash embeddings.
- Fallback JSON vector index when ChromaDB is unavailable.
- Lightweight training classifier using pure Python Naive Bayes.
- Jira dry-run and mock Jira push by default.
- Docker and local development support.

## Project Structure

```text
sprint-sarthi/
  frontend/              React app
  backend/               FastAPI app, models, sessions, file parsing
  agents/                Multi-agent orchestration and AI logic
  rag/                   ChromaDB/fallback retriever and ingestion
  knowledge_base/        Agile rules and templates
  training/              Lightweight classifier
  jira/                  Jira client
  data/                  Sessions and mock Jira storage
  docs/                  API contract, architecture, team plan, demo script
```


## One-Command Windows Git Bash Setup

If you are using Git Bash on a Windows machine, run everything with one command from the project root:

```bash
bash run-dev-gitbash.sh
```

This command creates `.venv`, installs backend requirements, creates `.env`, ingests the RAG knowledge base, installs frontend packages, and starts both FastAPI and React. You do not need to manually run `source .venv/Scripts/activate`.

Backend docs: `http://127.0.0.1:8000/docs`
Frontend: `http://localhost:5173`

After the first run, faster restart:

```bash
bash run-dev-gitbash.sh --skip-install --no-ingest
```

Setup only, without starting servers:

```bash
bash run-dev-gitbash.sh --setup-only
```

Backend only:

```bash
bash run-dev-gitbash.sh --backend-only
```

Frontend only:

```bash
bash run-dev-gitbash.sh --frontend-only
```

PowerShell or CMD users can run:

```bat
run-dev-windows.bat
```

More details are in `GIT_BASH_WINDOWS_RUN.md`.

## Local Backend Setup

```bash
cd sprint-sarthi
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m rag.ingest
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open backend docs:

```text
http://localhost:8000/docs
```

## Local Frontend Setup

```bash
cd sprint-sarthi/frontend
npm install
npm run dev
```

Open frontend:

```text
http://localhost:5173
```

## Docker Setup

```bash
cd sprint-sarthi
docker compose up --build
```

Frontend: `http://localhost:5173`
Backend: `http://localhost:8000`

## API Flow

1. `POST /api/analyze`
2. `POST /api/clarify`
3. `POST /api/generate-backlog`
4. `POST /api/plan-sprint`
5. `POST /api/jira-dry-run`
6. `POST /api/jira-push`

## Example Requirement

```text
Build Sprint Sarthi, an AI Agile planning assistant.
Target user: product owners, scrum masters, and hackathon teams.
Problem: messy requirements are converted directly into backlog items without enough clarification.
Business goal: reduce manual backlog and sprint planning effort.
Success metric: generate a reviewed backlog and sprint plan in under 5 minutes.
In scope: requirement input, file upload, clarification questions, backlog generation, estimation, sprint plan, Jira dry run.
Out of scope: advanced authentication, real-time collaboration, advanced analytics.
Dependencies: Jira API credentials, Agile knowledge base documents, FastAPI backend, React frontend.
Non functional requirements: secure file handling, clean JSON response, predictable output.
Deadline: hackathon demo sprint.
```

## AI Provider Modes

Default mode is `AI_PROVIDER=mock`. This runs deterministic local logic and requires no API key.

To use an OpenAI-compatible chat-completions endpoint, set:

```env
AI_PROVIDER=openai-compatible
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

If the LLM call fails, the system automatically falls back to deterministic local logic.

## Jira Modes

Default mode is mock:

```env
JIRA_MOCK_MODE=true
```

Mock Jira issues are written to:

```text
data/mock_jira_created.json
```

For real Jira Cloud, set `JIRA_MOCK_MODE=false` and configure `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, and `JIRA_PROJECT_KEY`.

## Team Ownership

- Frontend Owner: React screens and API calls.
- Backend Owner: FastAPI, endpoints, session management, file handling.
- AI Agent Owner: all agents, prompts, JSON control, clarification-first logic.
- RAG/Jira Owner: ChromaDB, knowledge ingestion, classifier, Jira dry run and push.

## Testing

```bash
python -m pytest tests
python -m py_compile $(find backend agents rag jira training tests -name '*.py')
```
