#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ "$(uname -s)" != "Linux" ]]; then
  printf '%s\n' "This bootstrap script supports Ubuntu/Linux. Install Docker Desktop on Windows or macOS, then run: docker compose up --build -d" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Installing Docker Engine and Compose..."
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-v2
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose is not installed. Installing the Compose plugin..."
  sudo apt-get update
  sudo apt-get install -y docker-compose-v2
fi

sudo systemctl enable --now docker

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
fi

echo "Building and starting Sprint Sarthi..."
"${DOCKER[@]}" compose up --build --detach --remove-orphans

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
SERVER_IP="${SERVER_IP:-localhost}"

echo
echo "Sprint Sarthi is running:"
echo "  Frontend: http://${SERVER_IP}:3000"
echo "  API:      http://${SERVER_IP}:8000"
echo "  Health:   http://${SERVER_IP}:8000/health"
echo
echo "View logs: docker compose logs -f"
echo "Stop:      docker compose down"
