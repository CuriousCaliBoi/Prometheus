#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi
uvicorn prometheus.conductor.app:app --host 0.0.0.0 --port 6060
