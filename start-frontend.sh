#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FRONTEND="$PROJECT_ROOT/frontend"

if [ ! -d "$FRONTEND/node_modules" ]; then
    printf '%s\n' "Frontend is not set up. Run ./setup-local.sh first." >&2
    exit 1
fi

cd "$FRONTEND"
BACKEND_INTERNAL_URL="http://127.0.0.1:8000" exec npx --yes pnpm@10.34.5 dev
