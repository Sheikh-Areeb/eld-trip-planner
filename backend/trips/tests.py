from django.test import TestCase

from .hos_calculator import HOSConfig, calculate_trip


class HOSCalculatorComplianceTests(TestCase):
    def _run_trip(
        self,
        distance_miles: float,
        cycle_used: float = 0.0,
        hos_config: HOSConfig | None = None,
        route_coords: list[list[float]] | None = None,
        current_to_pickup_distance_miles: float = 0.0,
    ):
        # Straight synthetic route for deterministic interpolation.
        route = route_coords or [[41.0, -87.0], [40.0, -88.0], [39.0, -89.0], [38.0, -90.0]]
        return calculate_trip(
            total_distance_miles=distance_miles,
            total_drive_time_hours=distance_miles / 55.0,
            pickup_lat=41.0,
            pickup_lng=-87.0,
            dropoff_lat=38.0,
            dropoff_lng=-90.0,
            route_coords=route,
            current_to_pickup_distance_miles=current_to_pickup_distance_miles,
            current_cycle_used_hours=cycle_used,
            start_time_hour=8.0,
            hos_config=hos_config,
        )

    def test_shift_limits_enforced(self):
        _, day_logs = self._run_trip(distance_miles=1500.0)
        periods = sorted(
            [p for day in day_logs for p in day.periods],
            key=lambda p: (p.start_hour, p.end_hour),
        )

        if not periods:
            self.fail("Expected duty periods for generated trip.")

        shift_start = periods[0].start_hour
        shift_drive = 0.0
        rest_accum = 0.0

        for period in periods:
            if period.status in ("off_duty", "sleeper"):
                rest_accum += period.duration
                if rest_accum >= 10.0:
                    shift_start = period.end_hour
                    shift_drive = 0.0
                continue

            rest_accum = 0.0

            if period.status == "driving":
                shift_drive += period.duration
                # 11-hour driving limit.
                self.assertLessEqual(shift_drive, 11.0001)
                # Driving must end within 14-hour window from shift start.
                self.assertLessEqual(period.end_hour - shift_start, 14.0001)

    def test_no_immediate_break_after_fuel_stop(self):
        # Distance chosen to guarantee at least one fueling stop.
        stops, _ = self._run_trip(distance_miles=2200.0)

        fuel_indexes = [idx for idx, stop in enumerate(stops) if stop.stop_type == "fuel"]
        self.assertTrue(fuel_indexes, "Expected at least one fuel stop for long trip.")

        for idx in fuel_indexes:
            if idx + 1 >= len(stops):
                continue
            next_stop = stops[idx + 1]
            # Fueling is a 30-min non-driving period and should satisfy break qualification.
            self.assertNotEqual(
                next_stop.stop_type,
                "break_30",
                "Unexpected mandatory break immediately after a fuel stop.",
            )

    def test_day_total_on_duty_includes_driving_and_on_duty_not_driving(self):
        _, day_logs = self._run_trip(distance_miles=300.0)

        for day in day_logs:
            expected = round(
                sum(
                    period.duration
                    for period in day.periods
                    if period.status in ("driving", "on_duty_not_driving")
                ),
                2,
            )
            self.assertEqual(day.total_on_duty, expected)

    def test_short_haul_cdl_exempts_30_min_break(self):
        config = HOSConfig(short_haul_mode="cdl_150")
        compact_route = [[41.0, -87.0], [41.5, -87.0], [41.0, -87.5], [41.2, -86.9]]
        stops, _ = self._run_trip(
            distance_miles=500.0,
            hos_config=config,
            route_coords=compact_route,
        )
        self.assertFalse(
            any(stop.stop_type == "break_30" for stop in stops),
            "CDL short-haul flow should not insert mandatory 30-minute break stops.",
        )

    def test_adverse_conditions_allow_extra_shift_capacity(self):
        base_stops, _ = self._run_trip(distance_miles=700.0, hos_config=HOSConfig())
        adverse_stops, _ = self._run_trip(
            distance_miles=700.0,
            hos_config=HOSConfig(adverse_driving_conditions=True),
        )
        base_rests = sum(1 for stop in base_stops if stop.stop_type == "rest")
        adverse_rests = sum(1 for stop in adverse_stops if stop.stop_type == "rest")
        self.assertLessEqual(
            adverse_rests,
            base_rests,
            "Adverse conditions should not cause stricter shift limits than baseline.",
        )

    def test_non_cdl_short_haul_cannot_use_16_hour_exception(self):
        with self.assertRaises(ValueError):
            self._run_trip(
                distance_miles=80.0,
                hos_config=HOSConfig(
                    short_haul_mode="non_cdl_150",
                    use_16_hour_exception=True,
                ),
            )

    def test_pickup_stop_occurs_after_first_leg_distance(self):
        first_leg = 120.0
        total = 340.0
        stops, _ = self._run_trip(
            distance_miles=total,
            current_to_pickup_distance_miles=first_leg,
        )
        pickup = next(stop for stop in stops if stop.stop_type == "pickup")
        self.assertAlmostEqual(pickup.odometer, first_leg, places=1)
