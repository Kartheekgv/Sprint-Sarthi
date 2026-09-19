#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' "Docker is required. Install Docker Desktop or Docker Engine with Compose, then run this script again." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  printf '%s\n' "Docker Compose is required. Install or update Docker Desktop/Compose, then run this script again." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  printf '%s\n' "Docker is not running. Start Docker Desktop or the Docker service, then run this script again." >&2
  exit 1
fi

echo "Building and starting Sprint Sarthi..."
export FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://localhost:3000}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-/api/v1}"
docker compose up --build --detach --remove-orphans

echo "Waiting for services..."
for attempt in {1..30}; do
  if curl --fail --silent http://localhost:3000/health >/dev/null \
    && curl --fail --silent http://localhost:3000 >/dev/null; then
    break
  fi
  if [[ "$attempt" == 30 ]]; then
    echo "Services did not become ready. Recent logs:" >&2
    docker compose ps >&2
    docker compose logs --tail=80 >&2
    exit 1
  fi
  sleep 2
done

echo
echo "Sprint Sarthi is running:"
echo "  Frontend: http://localhost:3000"
echo "  API:      http://localhost:3000/api/v1"
echo "  Health:   http://localhost:3000/health"
echo
echo "View logs: docker compose logs -f"
echo "Stop:      docker compose down"
