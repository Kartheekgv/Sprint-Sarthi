#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "Docker is not installed. Installing Docker Engine and Compose..."
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-v2
  else
    printf '%s\n' "Docker is required. Install Docker Desktop from https://docs.docker.com/get-docker/ and run this script again." >&2
    exit 1
  fi
fi

if ! docker compose version >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "Docker Compose is not installed. Installing the Compose plugin..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-v2
  else
    printf '%s\n' "Docker Compose is required. Update Docker Desktop and run this script again." >&2
    exit 1
  fi
fi

if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl enable --now docker
fi

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
fi

echo "Building and starting Sprint Sarthi..."
if [[ -z "${SPRINT_SARTHI_HOST:-}" ]]; then
  METADATA_TOKEN="$(curl --silent --max-time 2 -X PUT \
    -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' \
    http://169.254.169.254/latest/api/token || true)"
  SERVER_IP="$(curl --silent --max-time 2 \
    -H "X-aws-ec2-metadata-token: ${METADATA_TOKEN}" \
    http://169.254.169.254/latest/meta-data/public-ipv4 || true)"
else
  SERVER_IP="$SPRINT_SARTHI_HOST"
fi
SERVER_IP="${SERVER_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
SERVER_IP="${SERVER_IP:-localhost}"
if [[ -n "${SPRINT_SARTHI_HOST:-}" ]]; then
  export SPRINT_SARTHI_FRONTEND_PORT=80
elif [[ -z "${SPRINT_SARTHI_FRONTEND_PORT:-}" ]]; then
  export SPRINT_SARTHI_FRONTEND_PORT=3000
fi
FRONTEND_PORT="${SPRINT_SARTHI_FRONTEND_PORT:-3000}"
if [[ "$FRONTEND_PORT" == "80" ]]; then
  FRONTEND_URL="http://${SERVER_IP}"
else
  FRONTEND_URL="http://${SERVER_IP}:${FRONTEND_PORT}"
fi
export FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-${FRONTEND_URL}}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://${SERVER_IP}:8000/api/v1}"
"${DOCKER[@]}" compose up --build --detach --remove-orphans

echo "Waiting for services..."
for attempt in {1..30}; do
  if curl --fail --silent http://localhost:8000/health >/dev/null \
    && curl --fail --silent "http://localhost:${FRONTEND_PORT}" >/dev/null; then
    break
  fi
  if [[ "$attempt" == 30 ]]; then
    echo "Services did not become ready. Recent logs:" >&2
    "${DOCKER[@]}" compose ps >&2
    "${DOCKER[@]}" compose logs --tail=80 >&2
    exit 1
  fi
  sleep 2
done

echo
echo "Sprint Sarthi is running:"
echo "  Frontend: ${FRONTEND_URL}"
echo "  API:      http://${SERVER_IP}:8000"
echo "  Health:   http://${SERVER_IP}:8000/health"
echo
echo "View logs: docker compose logs -f"
echo "Stop:      docker compose down"
