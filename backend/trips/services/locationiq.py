"""
LocationIQ geocoding/routing service helpers.
"""

import requests
from django.conf import settings


LOCATIONIQ_REGION = getattr(settings, 'LOCATIONIQ_REGION', 'us')
LOCATIONIQ_HOST = f'{LOCATIONIQ_REGION}1.locationiq.com'
LOCATIONIQ_DIRECTIONS_BASE = f'https://{LOCATIONIQ_HOST}/v1/directions/driving'
LOCATIONIQ_API_KEY = getattr(settings, 'LOCATIONIQ_API_KEY', '').strip()

HEADERS = {
    'User-Agent': 'SpotterELDTripPlanner/1.0 (assessment@spotter.com)',
    'Accept': 'application/json',
}

ROUTE_TIMEOUT_SECONDS = 12


def get_route(start_lng, start_lat, end_lng, end_lat):
    if not LOCATIONIQ_API_KEY:
        raise ValueError('LocationIQ API key is missing. Set LOCATIONIQ_API_KEY in backend environment.')

    url = f'{LOCATIONIQ_DIRECTIONS_BASE}/{start_lng},{start_lat};{end_lng},{end_lat}'
    params = {
        'key': LOCATIONIQ_API_KEY,
        'steps': 'true',
        'overview': 'full',
        'geometries': 'geojson',
        'alternatives': 'false',
    }
    resp = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=ROUTE_TIMEOUT_SECONDS,
    )
    if resp.status_code >= 400:
        try:
            payload = resp.json()
            message = payload.get('error') or payload.get('message')
        except Exception:
            message = None
        if resp.status_code == 400:
            friendly = (
                "No drivable route found between the selected locations. "
                "Use specific city/state inputs within the same road-connected region."
            )
            if message:
                raise ValueError(f"{friendly} Provider message: {message}")
            raise ValueError(friendly)
        resp.raise_for_status()

    data = resp.json()
    routes = data.get('routes', [])
    if not routes:
        raise ValueError(data.get('error', 'LocationIQ returned no route results.'))

    route = routes[0]
    distance_m = route.get('distance', 0.0)
    duration_s = route.get('duration', 0.0)
    coords_raw = route.get('geometry', {}).get('coordinates', [])
    lat_lngs = [[c[1], c[0]] for c in coords_raw]

    instructions = []
    for leg in route.get('legs', []):
        for step in leg.get('steps', []):
            maneuver = step.get('maneuver', {})
            step_name = step.get('name', '')
            step_type = maneuver.get('type', '').replace('_', ' ').strip()
            modifier = maneuver.get('modifier', '').strip()
            parts = [p for p in [step_type, modifier] if p]
            action = " ".join(parts).strip().title() or "Continue"
            road = f" on {step_name}" if step_name else ""
            instructions.append({
                'instruction': f"{action}{road}",
                'distance_miles': round(step.get('distance', 0) * 0.000621371, 2),
                'duration_minutes': round(step.get('duration', 0) / 60.0, 1),
            })

    start_name = ''
    end_name = ''
    waypoints = data.get('waypoints') or route.get('waypoints') or []
    if len(waypoints) >= 2:
        start_name = str(waypoints[0].get('name') or '').strip()
        end_name = str(waypoints[-1].get('name') or '').strip()

    return {
        'distance_miles': distance_m * 0.000621371,
        'duration_hours': duration_s / 3600.0,
        'coordinates': lat_lngs,
        'instructions': instructions,
        'start_name': start_name,
        'end_name': end_name,
    }
