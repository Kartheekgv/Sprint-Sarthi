#!/usr/bin/env bash
set -e

# One-command runner for Windows Git Bash.
# It does not require manual virtual environment activation.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python >/dev/null 2>&1; then
  python run_dev.py "$@"
elif command -v python3 >/dev/null 2>&1; then
  python3 run_dev.py "$@"
elif command -v py >/dev/null 2>&1; then
  py -3 run_dev.py "$@"
else
  echo "Python was not found. Install Python 3.10+ and try again."
  exit 1
fi
