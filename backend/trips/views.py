"""Views for the trips API."""

from requests import RequestException, Timeout
from requests import HTTPError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers as drf_serializers

from .hos_calculator import HOSConfig, calculate_trip, stops_to_dict, day_logs_to_dict
from .models import TripPlan
from .services.locationiq import get_route
from .serializers import TripPlanRequestSerializer


class PlanTripView(APIView):
    """
    POST /api/trips/plan/
    Body: { current_location, pickup_location, dropoff_location, current_cycle_used }
    """

    def post(self, request):
        serializer = TripPlanRequestSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except drf_serializers.ValidationError as exc:
            return Response(
                {'error': exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        validated = serializer.validated_data
        current_loc = validated['current_location']
        pickup_loc = validated['pickup_location']
        dropoff_loc = validated['dropoff_location']
        cycle_used = validated['current_cycle_used']
        cycle_rule = validated['cycle_rule']
        adverse_driving_conditions = validated['adverse_driving_conditions']
        short_haul_mode = validated['short_haul_mode']
        use_16_hour_exception = validated['use_16_hour_exception']
        used_16_hour_in_last_7_days = validated['used_16_hour_in_last_7_days']
        return_to_reporting_location = validated['return_to_reporting_location']
        enable_34h_restart = validated['enable_34h_restart']

        cycle_max = 60 if cycle_rule == '60_7' else 70
        current_geo = TripPlanRequestSerializer.to_trip_point(current_loc, 'current_location')
        pickup_geo = TripPlanRequestSerializer.to_trip_point(pickup_loc, 'pickup_location')
        dropoff_geo = TripPlanRequestSerializer.to_trip_point(dropoff_loc, 'dropoff_location')

        # ── Route ─────────────────────────────────────────────
        try:
            route1 = get_route(
                current_geo['lng'], current_geo['lat'],
                pickup_geo['lng'],  pickup_geo['lat'],
            )
            route2 = get_route(
                pickup_geo['lng'],  pickup_geo['lat'],
                dropoff_geo['lng'], dropoff_geo['lat'],
            )
        except Timeout:
            return Response(
                {
                    'error': (
                        'Routing timed out while contacting LocationIQ. '
                        'Please retry in a moment.'
                )
            },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except RequestException as e:
            if isinstance(e, HTTPError):
                status_code = e.response.status_code
                try:
                    details = e.response.json()
                    provider_msg = details.get('error') or details.get('message')
                except Exception:
                    provider_msg = None
                if status_code == 429:
                    return Response(
                        {
                            'error': (
                                'Routing rate limit reached at routing provider. '
                                'Please retry in 1-2 minutes.'
                                + (f" {provider_msg}" if provider_msg else "")
                            )
                        },
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                    )
                return Response(
                    {
                        'error': (
                            f"Routing request failed with status {status_code}."
                            + (f" {provider_msg}" if provider_msg else "")
                        )
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            return Response(
                {'error': 'Routing service request failed. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            return Response(
                {'error': f'Routing failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Use provider waypoint names only when available.
        current_geo['label'] = route1.get('start_name', '')
        pickup_geo['label'] = route1.get('end_name', '') or route2.get('start_name', '')
        dropoff_geo['label'] = route2.get('end_name', '')

        total_distance  = route1['distance_miles'] + route2['distance_miles']
        total_drive_hrs = route1['duration_hours']  + route2['duration_hours']
        all_coords      = route1['coordinates'] + route2['coordinates']
        effective_speed_mph = (
            total_distance / total_drive_hrs
            if total_distance > 0 and total_drive_hrs > 0
            else 55.0
        )

        # ── HOS Calculation ───────────────────────────────────
        try:
            hos_config = HOSConfig(
                cycle_rule=cycle_rule,
                adverse_driving_conditions=adverse_driving_conditions,
                short_haul_mode=short_haul_mode,
                use_16_hour_exception=use_16_hour_exception,
                used_16_hour_in_last_7_days=used_16_hour_in_last_7_days,
                return_to_reporting_location=return_to_reporting_location,
                enable_34h_restart=enable_34h_restart,
            )
            stops, day_logs = calculate_trip(
                total_distance_miles    = total_distance,
                total_drive_time_hours  = total_drive_hrs,
                pickup_lat              = pickup_geo['lat'],
                pickup_lng              = pickup_geo['lng'],
                dropoff_lat             = dropoff_geo['lat'],
                dropoff_lng             = dropoff_geo['lng'],
                route_coords            = all_coords,
                current_to_pickup_distance_miles = route1['distance_miles'],
                current_cycle_used_hours= cycle_used,
                start_time_hour         = 8.0,
                hos_config              = hos_config,
            )
        except Exception as e:
            return Response(
                {'error': f'HOS calculation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_payload = {
            'trip': {
                'current_location': current_geo,
                'pickup_location':  pickup_geo,
                'dropoff_location': dropoff_geo,
                'current_cycle_used': round(cycle_used, 2),
                'planned_start_hour': 8.0,
                'total_distance_miles': round(total_distance,  1),
                'total_drive_hours':    round(total_drive_hrs, 2),
                'effective_speed_mph':  round(effective_speed_mph, 2),
                'num_days': len(day_logs),
            },
            'hos_rules_applied': {
                'cycle_rule': cycle_rule,
                'cycle_limit_hours': cycle_max,
                'adverse_driving_conditions': adverse_driving_conditions,
                'short_haul_mode': short_haul_mode,
                'use_16_hour_exception': use_16_hour_exception,
                'used_16_hour_in_last_7_days': used_16_hour_in_last_7_days,
                'return_to_reporting_location': return_to_reporting_location,
                'enable_34h_restart': enable_34h_restart,
            },
            'route': {
                'segment1': {
                    'coordinates':    route1['coordinates'],
                    'distance_miles': round(route1['distance_miles'], 1),
                    'duration_hours': round(route1['duration_hours'],  2),
                    'instructions':   route1['instructions'],
                },
                'segment2': {
                    'coordinates':    route2['coordinates'],
                    'distance_miles': round(route2['distance_miles'], 1),
                    'duration_hours': round(route2['duration_hours'],  2),
                    'instructions':   route2['instructions'],
                },
                'all_coordinates': all_coords,
                'instructions': route1['instructions'] + route2['instructions'],
            },
            'stops':    stops_to_dict(stops),
            'eld_logs': day_logs_to_dict(day_logs),
        }

        trip_plan = TripPlan.objects.create(
            current_location=current_loc,
            pickup_location=pickup_loc,
            dropoff_location=dropoff_loc,
            current_cycle_used=cycle_used,
            response_payload=response_payload,
        )

        return Response({
            **response_payload,
            'plan_id': trip_plan.id,
            'created_at': trip_plan.created_at.isoformat(),
        })


class TripPlanLatestView(APIView):
    """GET /api/trips/plans/latest/"""

    def get(self, request):
        plan = TripPlan.objects.first()
        if not plan:
            return Response(
                {'error': 'No saved trip plans yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = dict(plan.response_payload or {})
        trip = dict(payload.get('trip') or {})
        if 'current_cycle_used' not in trip:
            trip['current_cycle_used'] = round(plan.current_cycle_used, 2)
        payload['trip'] = trip

        return Response({
            **payload,
            'plan_id': plan.id,
            'created_at': plan.created_at.isoformat(),
        })


class TripPlanRecentView(APIView):
    """GET /api/trips/plans/recent/?limit=5"""

    def get(self, request):
        limit_raw = request.query_params.get('limit', '5')
        try:
            limit = max(1, min(20, int(limit_raw)))
        except (TypeError, ValueError):
            limit = 5

        plans = TripPlan.objects.all()[:limit]
        result = []
        for plan in plans:
            payload = dict(plan.response_payload or {})
            trip = dict(payload.get('trip') or {})
            if 'current_cycle_used' not in trip:
                trip['current_cycle_used'] = round(plan.current_cycle_used, 2)
            payload['trip'] = trip
            result.append({
                **payload,
                'plan_id': plan.id,
                'created_at': plan.created_at.isoformat(),
            })

        return Response({'plans': result})
