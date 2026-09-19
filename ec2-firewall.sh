#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

if ! command -v ufw >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ufw
fi

ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'Sprint Sarthi frontend'
ufw allow 8000/tcp comment 'Sprint Sarthi API'
ufw --force enable
ufw status verbose
