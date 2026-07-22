#!/bin/sh
# Start the API immediately. Seed is available via POST /seed endpoint.
echo "Starting API on port ${PORT:-8000}..."
exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
