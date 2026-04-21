#!/bin/bash
# Startup script for Railway
# Use PORT from environment (Railway default) or fallback to 8000

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "🚀 Starting FastAPI on $HOST:$PORT"
exec uvicorn main:app --host "$HOST" --port "$PORT"
