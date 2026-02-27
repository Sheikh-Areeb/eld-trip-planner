#!/usr/bin/env sh
set -e

if [ -d backend ]; then
  cd backend
fi

python manage.py migrate
exec uvicorn spotter.asgi:application --host 0.0.0.0 --port "$PORT"
