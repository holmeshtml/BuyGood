#!/bin/sh
# Seed the database on startup, then run the API.
echo "Seeding Postgres..."
python gen.py --postgres --days 30
echo "Starting API..."
exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
