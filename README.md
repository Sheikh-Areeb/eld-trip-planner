# Spotter ELD Trip Planner

Full-stack assessment app using Django + React to plan property-carrier trips with HOS constraints, map output, and ELD daily logs.

## Features and assumptions
- Inputs:
  - Current location
  - Pickup location
  - Dropoff location
  - Current cycle used (hours)
- Outputs:
  - Route map with stops/rests
  - Multi-day ELD log sheets
- Assumptions:
  - Property-carrying driver
  - 70 hours / 8 days
  - No adverse driving conditions
  - Fuel every 1,000 miles
  - 1 hour pickup and 1 hour dropoff

## Tech stack
- Backend: Django + Django REST Framework
- Frontend: React + Vite + Leaflet
- Database: PostgreSQL
- Maps/routing/geocoding/tiles: LocationIQ

## Local setup

### 1) Backend
```bash
cd backend
python -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

### 2) Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Environment variables

### Backend (`backend/.env`)
- `LOCATIONIQ_API_KEY`
- `LOCATIONIQ_REGION`
- `SECRET_KEY`
- `DEBUG`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_SSLMODE`

### Frontend (`frontend/.env`)
- `VITE_API_URL`
- `VITE_LOCATIONIQ_KEY`
- `VITE_LOCATIONIQ_REGION`

## Deployment (recommended)

### Backend (Render)
1. Create a new Web Service from `backend/`.
2. Build command: `pip install -r requirements.txt`
3. Start command: `python manage.py migrate && uvicorn spotter.asgi:application --host 0.0.0.0 --port $PORT`
4. Set required backend environment variables.
5. Copy backend URL, for example `https://your-backend.onrender.com`.

### Frontend (Vercel)
1. Import this repo in Vercel.
2. Set project root to `frontend`.
3. Set:
   - `VITE_API_URL=https://your-backend.onrender.com/api`
   - `VITE_LOCATIONIQ_KEY=<your-locationiq-key>`
4. Deploy.

## Submission checklist
- Push repo with both `backend/` and `frontend/`
- Add hosted frontend URL
- Add 3-5 minute Loom URL
- Mention assumptions and known limitations
