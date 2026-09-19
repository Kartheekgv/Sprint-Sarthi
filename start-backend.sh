#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKEND="$PROJECT_ROOT/backend"
PYTHON="$BACKEND/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    printf '%s\n' "Backend is not set up. Run ./setup-local.sh first." >&2
    exit 1
fi

cd "$BACKEND"
exec "$PYTHON" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
