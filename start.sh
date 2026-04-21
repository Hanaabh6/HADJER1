#!/usr/bin/env sh
set -eu

PORT_VALUE="${PORT:-8000}"

exec uvicorn main:app --host 0.0.0.0 --port "${PORT_VALUE}"
