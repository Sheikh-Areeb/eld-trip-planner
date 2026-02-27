#!/usr/bin/env sh
set -e
cd backend
python manage.py migrate
exec uvicorn spotter.asgi:application --host 0.0.0.0 --port "$PORT"
