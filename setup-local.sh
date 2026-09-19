#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BACKEND="$PROJECT_ROOT/backend"
FRONTEND="$PROJECT_ROOT/frontend"

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    printf '%s\n' "Python 3.11 or newer is required." >&2
    exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npx >/dev/null 2>&1; then
    printf '%s\n' "Node.js 20 or newer is required." >&2
    exit 1
fi

if [ ! -x "$BACKEND/.venv/bin/python" ]; then
    "$PYTHON" -m venv "$BACKEND/.venv"
fi

PYTHON="$BACKEND/.venv/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e "$BACKEND[test]"

if [ ! -f "$BACKEND/.env" ]; then
    cp "$BACKEND/.env.example" "$BACKEND/.env"
fi

(
    cd "$BACKEND"
    .venv/bin/alembic upgrade head
)

(
    cd "$FRONTEND"
    npx --yes pnpm@10.34.5 install --frozen-lockfile
)

printf '%s\n' "Setup complete. Start the backend and frontend in separate terminals."
