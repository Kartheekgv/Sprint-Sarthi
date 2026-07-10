#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
exec bash run-dev-gitbash.sh --backend-only "$@"
