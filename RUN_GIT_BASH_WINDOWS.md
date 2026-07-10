# Run Sprint Sarthi on Windows Git Bash

Open Git Bash inside the project root and run:

```bash
bash run-dev-gitbash.sh
```

This single command will:

1. Create `.venv`
2. Install backend requirements
3. Create `.env` files
4. Ingest the RAG knowledge base
5. Install frontend npm packages
6. Start FastAPI and React/Vite

If `npm` is missing, the runner will try to install Node.js LTS automatically using `winget`. If your company laptop blocks `winget`, install Node.js LTS manually, close Git Bash, reopen Git Bash, and run the same command again.

After successful startup:

```text
Backend Swagger: http://127.0.0.1:8000/docs
Frontend UI:     http://localhost:5173
```

Useful commands:

```bash
# Start backend only
bash run-dev-gitbash.sh --backend-only

# Start frontend only after backend is already running
bash run-dev-gitbash.sh --frontend-only

# Faster restart after first successful setup
bash run-dev-gitbash.sh --skip-install --no-ingest

# Disable automatic Node.js installation attempt
bash run-dev-gitbash.sh --no-auto-install-node
```
