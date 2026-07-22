#!/bin/sh
# Start the API immediately, seed in background so healthcheck passes.
echo "Starting API..."
python gen.py --postgres --days 30 &
exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
