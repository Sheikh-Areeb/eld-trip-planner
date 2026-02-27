"""
LocationIQ geocoding/routing service helpers.
"""

import requests
from requests import HTTPError
from django.conf import settings


LOCATIONIQ_REGION = getattr(settings, 'LOCATIONIQ_REGION', 'us')
LOCATIONIQ_HOST = f'{LOCATIONIQ_REGION}1.locationiq.com'
LOCATIONIQ_GEOCODE_URL = f'https://{LOCATIONIQ_HOST}/v1/search.php'
LOCATIONIQ_DIRECTIONS_BASE = f'https://{LOCATIONIQ_HOST}/v1/directions/driving'
LOCATIONIQ_API_KEY = getattr(settings, 'LOCATIONIQ_API_KEY', '').strip()

HEADERS = {
    'User-Agent': 'SpotterELDTripPlanner/1.0 (assessment@spotter.com)',
    'Accept': 'application/json',
}

GEOCODE_TIMEOUT_SECONDS = 5
ROUTE_TIMEOUT_SECONDS = 12

LOCATION_CODE_ALIASES = {
    'CHI': 'Chicago, IL, USA',
    'CHI,IL': 'Chicago, IL, USA',
    'ORD': 'Chicago, IL, USA',
    'MDW': 'Chicago, IL, USA',
    'IND': 'Indianapolis, IN, USA',
    'BNA': 'Nashville, TN, USA',
    'NSH': 'Nashville, TN, USA',
    'NYC': 'New York, NY, USA',
    'LAX': 'Los Angeles, CA, USA',
    'SFO': 'San Francisco, CA, USA',
    'SEA': 'Seattle, WA, USA',
    'ATL': 'Atlanta, GA, USA',
    'DFW': 'Dallas, TX, USA',
    'MIA': 'Miami, FL, USA',
}


def _candidate_geocode_queries(raw_query: str):
    q = (raw_query or '').strip()
    if not q:
        return []

    normalized = q.upper().replace(' ', '')
    if normalized in LOCATION_CODE_ALIASES:
        return [LOCATION_CODE_ALIASES[normalized], q]

    candidates = [q]
    if q.isalpha() and len(q) <= 5:
        candidates.append(f'{q}, USA')
    if q.isdigit() and len(q) == 5:
        candidates.append(f'{q}, USA')

    seen = set()
    deduped = []
    for item in candidates:
        key = item.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def geocode_location(query: str):
    if not LOCATIONIQ_API_KEY:
        raise ValueError('LocationIQ API key is missing. Set LOCATIONIQ_API_KEY in backend environment.')

    last_http_error = None
    for candidate in _candidate_geocode_queries(query):
        params = {
            'key': LOCATIONIQ_API_KEY,
            'q': candidate,
            'format': 'json',
            'limit': 1,
            'addressdetails': 0,
            'countrycodes': 'us',
        }
        resp = requests.get(
            LOCATIONIQ_GEOCODE_URL,
            params=params,
            headers=HEADERS,
            timeout=GEOCODE_TIMEOUT_SECONDS,
        )
        try:
            resp.raise_for_status()
        except HTTPError as err:
            last_http_error = err
            continue

        results = resp.json()
        if not results:
            continue

        first = results[0]
        label = first.get('display_name', candidate)
        return {
            'lat': float(first['lat']),
            'lng': float(first['lon']),
            'label': str(label).split(',')[0].strip(),
        }

    if last_http_error:
        raise last_http_error

    raise ValueError(
        f"Could not find location: '{query}'. "
        "You can use full names or codes like CHI, IND, BNA."
    )


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

    return {
        'distance_miles': distance_m * 0.000621371,
        'duration_hours': duration_s / 3600.0,
        'coordinates': lat_lngs,
        'instructions': instructions,
    }
