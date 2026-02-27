"""
HOS Calculator for Property-Carrying Drivers
Rules:
- 70 hours / 8 days rolling window
- 11-hour driving limit per shift
- 14-hour driving window per shift (elapsed, not paused by short breaks)
- 10-hour off-duty rest (resets 11-hr and 14-hr clocks)
- 30-minute break required after 8 cumulative hours driving (any 30-min non-driving period qualifies)
- Fuel stop every 1,000 miles
- 1 hour pickup stop, 1 hour dropoff stop
- Average driving speed: 55 mph
"""

from dataclasses import dataclass, field
from typing import List, Optional
from math import asin, cos, radians, sin, sqrt


@dataclass
class HOSConfig:
    cycle_rule: str = '70_8'  # '70_8' or '60_7'
    adverse_driving_conditions: bool = False
    short_haul_mode: str = 'none'  # 'none', 'cdl_150', 'non_cdl_150'
    use_16_hour_exception: bool = False
    used_16_hour_in_last_7_days: bool = False
    return_to_reporting_location: bool = True
    enable_34h_restart: bool = True


@dataclass
class Stop:
    stop_type: str          # 'start', 'pickup', 'dropoff', 'fuel', 'rest', 'break_30', 'sleeper'
    label: str
    location: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    arrive_hour: float      # Hours since trip start
    depart_hour: float
    odometer: float         # Miles from trip start
    notes: str = ''


@dataclass
class DutyPeriod:
    """A segment of duty status"""
    status: str             # 'off_duty', 'sleeper', 'driving', 'on_duty_not_driving'
    start_hour: float       # Hours since midnight of day 0
    end_hour: float
    day: int                # 0-indexed
    notes: str = ''

    @property
    def duration(self) -> float:
        return self.end_hour - self.start_hour


@dataclass
class DayLog:
    day: int                # 0-indexed
    date_label: str
    periods: List[DutyPeriod] = field(default_factory=list)
    total_driving: float = 0.0
    total_on_duty: float = 0.0
    total_off_duty: float = 0.0
    odometer_start: float = 0.0
    odometer_end: float = 0.0
    remarks: List[str] = field(default_factory=list)


def calculate_trip(
    total_distance_miles: float,
    total_drive_time_hours: float,
    pickup_lat: float,
    pickup_lng: float,
    dropoff_lat: float,
    dropoff_lng: float,
    route_coords: List[List[float]],
    current_to_pickup_distance_miles: float = 0.0,
    current_cycle_used_hours: float = 0.0,
    start_time_hour: float = 8.0,        # Start at 8 AM
    hos_config: Optional[HOSConfig] = None,
):
    """
    Main HOS trip calculator.
    Returns (stops, day_logs) where day_logs contains per-day duty periods.
    """

    config = hos_config or HOSConfig()

    if config.short_haul_mode not in ('none', 'cdl_150', 'non_cdl_150'):
        raise ValueError('short_haul_mode must be one of: none, cdl_150, non_cdl_150.')
    if config.cycle_rule not in ('70_8', '60_7'):
        raise ValueError('cycle_rule must be one of: 70_8, 60_7.')
    if config.short_haul_mode == 'non_cdl_150' and config.use_16_hour_exception:
        raise ValueError('16-hour short-haul exception cannot be combined with non-CDL short-haul mode.')

    AVG_SPEED_MPH = 55.0
    base_drive_limit = 11.0
    base_window_limit = 14.0

    # Adverse conditions: +2 driving and +2 window for this trip plan.
    if config.adverse_driving_conditions:
        base_drive_limit += 2.0
        base_window_limit += 2.0

    # 16-hour exception may be used once every 7 days when eligible.
    eligible_for_16h = (
        config.use_16_hour_exception
        and not config.used_16_hour_in_last_7_days
        and config.return_to_reporting_location
    )
    one_time_window_limit = base_window_limit + 2.0 if eligible_for_16h else base_window_limit

    MAX_DRIVE_PER_SHIFT = base_drive_limit
    MAX_WINDOW_PER_SHIFT = base_window_limit
    MIN_REST = 10.0                  # hours off-duty to reset
    BREAK_THRESHOLD = 8.0           # hours of driving before mandatory break
    BREAK_DURATION = 0.5            # 30 minutes
    FUEL_INTERVAL_MILES = 1000.0
    PICKUP_DURATION = 1.0           # hours
    DROPOFF_DURATION = 1.0          # hours
    if config.cycle_rule == '60_7':
        MAX_CYCLE_HOURS = 60.0
    else:
        MAX_CYCLE_HOURS = 70.0

    break_required = config.short_haul_mode == 'none'

    # Interpolation helper: find lat/lng at a given mileage along route
    def interpolate_location(miles_from_start: float) -> tuple:
        if not route_coords or len(route_coords) < 2:
            return (pickup_lat, pickup_lng)
        
        # Build cumulative distance array
        cumulative = [0.0]
        for i in range(1, len(route_coords)):
            lat1, lon1 = route_coords[i-1]
            lat2, lon2 = route_coords[i]
            # Simple equirectangular approximation
            dlat = (lat2 - lat1) * 111.0
            dlon = (lon2 - lon1) * 111.0 * 0.7  # rough cos(lat) correction
            dist_km = (dlat**2 + dlon**2) ** 0.5
            dist_miles = dist_km * 0.621371
            cumulative.append(cumulative[-1] + dist_miles)
        
        total = cumulative[-1]
        if total == 0:
            return (route_coords[0][0], route_coords[0][1])
        
        target = miles_from_start
        for i in range(1, len(cumulative)):
            if cumulative[i] >= target or i == len(cumulative) - 1:
                seg_start = cumulative[i-1]
                seg_end = cumulative[i]
                seg_len = seg_end - seg_start
                if seg_len == 0:
                    t = 0
                else:
                    t = (target - seg_start) / seg_len
                t = max(0, min(1, t))
                lat = route_coords[i-1][0] + t * (route_coords[i][0] - route_coords[i-1][0])
                lon = route_coords[i-1][1] + t * (route_coords[i][1] - route_coords[i-1][1])
                return (lat, lon)
        
        return (route_coords[-1][0], route_coords[-1][1])

    def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        earth_radius_miles = 3958.8
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        )
        c = 2 * asin(sqrt(max(0.0, min(1.0, a))))
        return earth_radius_miles * c

    if config.short_haul_mode != 'none':
        # Approximation: ensure all route coordinates stay within 150 air miles from reporting location.
        # Reporting location is treated as pickup for this planner's workflow.
        max_radius = 0.0
        for lat, lng in route_coords:
            max_radius = max(max_radius, haversine_miles(pickup_lat, pickup_lng, lat, lng))
        if max_radius > 150.0:
            raise ValueError(
                f'Short-haul mode selected but route exceeds 150 air-mile radius ({max_radius:.1f} miles).'
            )

    stops: List[Stop] = []
    day_logs: List[DayLog] = []

    # --- State variables ---
    current_hour = start_time_hour      # absolute hour since day 0 midnight
    odometer = 0.0
    pickup_odometer_target = max(0.0, min(total_distance_miles, current_to_pickup_distance_miles))
    dropoff_odometer_target = max(pickup_odometer_target, total_distance_miles)

    # Shift state
    shift_start_hour = current_hour      # time when current shift started
    shift_drive_hours = 0.0              # driving this shift
    drive_since_break = 0.0              # cumulative driving since last qualifying 30-min non-driving period
    active_window_limit = one_time_window_limit

    # Cycle state — tracks on-duty hours
    cycle_used = current_cycle_used_hours  # hours used in current cycle

    # Fuel tracking
    miles_since_fuel = 0.0

    # Day tracking
    current_day = int(current_hour // 24)
    current_day_log = DayLog(
        day=current_day,
        date_label=f"Day {current_day + 1}",
        odometer_start=odometer
    )
    day_logs.append(current_day_log)

    def get_or_create_day(abs_hour: float) -> DayLog:
        nonlocal current_day_log
        day_idx = int(abs_hour // 24)
        if day_idx != current_day_log.day:
            current_day_log.odometer_end = odometer
            new_day = DayLog(
                day=day_idx,
                date_label=f"Day {day_idx + 1}",
                odometer_start=odometer
            )
            day_logs.append(new_day)
            current_day_log = new_day
        return current_day_log

    def add_period(status: str, start: float, end: float, notes: str = ''):
        if end <= start:
            return
        day = get_or_create_day(start)
        # If period crosses midnight, split it
        midnight = (int(start // 24) + 1) * 24.0
        if end > midnight and status in ('driving', 'on_duty_not_driving', 'off_duty', 'sleeper'):
            # Split at midnight
            add_period(status, start, midnight, notes)
            add_period(status, midnight, end, notes)
            return
        
        period = DutyPeriod(
            status=status,
            start_hour=start,
            end_hour=end,
            day=int(start // 24),
            notes=notes
        )
        day.periods.append(period)
        dur = end - start
        if status == 'driving':
            day.total_driving += dur
        elif status in ('on_duty_not_driving',):
            day.total_on_duty += dur
        elif status in ('off_duty', 'sleeper'):
            day.total_off_duty += dur

    def add_non_driving_period(
        status: str,
        duration_hours: float,
        notes: str,
        stop_type: str,
        stop_label: str,
        stop_notes: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ):
        """
        Adds a non-driving period and updates counters.
        Returns (start_hour, end_hour) for convenience.
        """
        nonlocal current_hour, cycle_used, drive_since_break

        start = current_hour
        end = start + duration_hours
        add_period(status, start, end, notes)

        stops.append(Stop(
            stop_type=stop_type,
            label=stop_label,
            location=None,
            lat=lat,
            lng=lng,
            arrive_hour=start,
            depart_hour=end,
            odometer=odometer,
            notes=stop_notes,
        ))

        # Only on-duty-not-driving contributes to cycle hours.
        if status == 'on_duty_not_driving':
            cycle_used += duration_hours

        # FMCSA break rule: any consecutive 30-minute non-driving period qualifies.
        if duration_hours >= BREAK_DURATION:
            drive_since_break = 0.0

        current_hour = end
        return start, end

    # === Add START marker ===
    stops.append(Stop(
        stop_type='start',
        label='Trip Start / Current Location',
        location=None,
        lat=route_coords[0][0] if route_coords else None,
        lng=route_coords[0][1] if route_coords else None,
        arrive_hour=current_hour,
        depart_hour=current_hour,
        odometer=0.0
    ))

    def drive_until_target(target_odometer: float):
        """
        Drive with HOS constraints until odometer reaches target_odometer.
        """
        nonlocal current_hour, odometer, miles_since_fuel
        nonlocal shift_start_hour, shift_drive_hours, drive_since_break, active_window_limit, cycle_used

        target_odometer = max(target_odometer, odometer)

        while odometer + 0.01 < target_odometer:
            get_or_create_day(current_hour)

            # --- Check: need mandatory 30-min break? ---
            if break_required and drive_since_break >= BREAK_THRESHOLD:
                add_non_driving_period(
                    status='off_duty',
                    duration_hours=BREAK_DURATION,
                    notes='30-min mandatory break',
                    stop_type='break_30',
                    stop_label='Mandatory 30-Min Break',
                    stop_notes='Required break after 8 hours driving',
                )

            # --- Check: cycle headroom ---
            cycle_headroom = MAX_CYCLE_HOURS - cycle_used
            if cycle_headroom <= 0:
                if not config.enable_34h_restart:
                    raise ValueError(
                        'No remaining cycle hours. Enable 34-hour restart or reduce current_cycle_used.'
                    )
                add_non_driving_period(
                    status='off_duty',
                    duration_hours=34.0,
                    notes='34-hr restart (70-hr cycle reset)',
                    stop_type='rest',
                    stop_label='34-Hour Restart (Cycle Reset)',
                    stop_notes='70-hr cycle limit reached. 34-hr restart required.',
                )
                cycle_used = 0.0
                shift_start_hour = current_hour
                shift_drive_hours = 0.0
                drive_since_break = 0.0
                active_window_limit = MAX_WINDOW_PER_SHIFT
                continue

            # --- Check: shift limits exhausted — need 10-hr rest ---
            window_remaining = active_window_limit - (current_hour - shift_start_hour)
            drive_remaining = MAX_DRIVE_PER_SHIFT - shift_drive_hours
            if drive_remaining <= 0 or window_remaining <= 0:
                add_non_driving_period(
                    status='sleeper',
                    duration_hours=MIN_REST,
                    notes='10-hr off-duty rest',
                    stop_type='rest',
                    stop_label='Required 10-Hour Rest',
                    stop_notes='10-hour rest period (resets driving limits)',
                )
                shift_start_hour = current_hour
                shift_drive_hours = 0.0
                drive_since_break = 0.0
                active_window_limit = MAX_WINDOW_PER_SHIFT
                continue

            # --- Check: fuel stop needed now ---
            miles_to_fuel = FUEL_INTERVAL_MILES - miles_since_fuel
            if miles_to_fuel <= 0:
                fuel_lat, fuel_lng = interpolate_location(odometer)
                add_non_driving_period(
                    status='on_duty_not_driving',
                    duration_hours=0.5,
                    notes='Fueling stop',
                    stop_type='fuel',
                    stop_label='Fuel Stop',
                    stop_notes='Refueling stop',
                    lat=fuel_lat,
                    lng=fuel_lng,
                )
                miles_since_fuel = 0.0
                continue

            # --- Determine this drive segment ---
            drive_available = min(
                MAX_DRIVE_PER_SHIFT - shift_drive_hours,
                active_window_limit - (current_hour - shift_start_hour),
                (BREAK_THRESHOLD - drive_since_break) if break_required else MAX_DRIVE_PER_SHIFT,
                MAX_CYCLE_HOURS - cycle_used,
            )
            drive_available = max(0.0, drive_available)
            if drive_available <= 0:
                continue

            miles_before_fuel = FUEL_INTERVAL_MILES - miles_since_fuel
            miles_remaining_phase = max(0.0, target_odometer - odometer)
            miles_this_segment = min(
                drive_available * AVG_SPEED_MPH,
                miles_before_fuel,
                miles_remaining_phase,
            )
            if miles_this_segment <= 0:
                continue

            hours_this_segment = miles_this_segment / AVG_SPEED_MPH
            drive_start = current_hour
            drive_end = current_hour + hours_this_segment
            add_period('driving', drive_start, drive_end)

            odometer += miles_this_segment
            miles_since_fuel += miles_this_segment
            shift_drive_hours += hours_this_segment
            drive_since_break += hours_this_segment
            cycle_used += hours_this_segment
            current_hour = drive_end

            # Fuel exactly on threshold between segments.
            if miles_since_fuel >= FUEL_INTERVAL_MILES and odometer + 0.01 < target_odometer:
                fuel_lat, fuel_lng = interpolate_location(odometer)
                add_non_driving_period(
                    status='on_duty_not_driving',
                    duration_hours=0.5,
                    notes='Fueling stop',
                    stop_type='fuel',
                    stop_label='Fuel Stop',
                    stop_notes='Refueling stop',
                    lat=fuel_lat,
                    lng=fuel_lng,
                )
                miles_since_fuel = 0.0

    # Phase 1: current -> pickup
    drive_until_target(pickup_odometer_target)

    # Phase 2 marker: pickup dwell time
    add_non_driving_period(
        status='on_duty_not_driving',
        duration_hours=PICKUP_DURATION,
        notes='Pickup stop',
        stop_type='pickup',
        stop_label='Pickup Location',
        stop_notes='1 hour pickup time',
        lat=pickup_lat,
        lng=pickup_lng,
    )
    # Phase 3: pickup -> dropoff
    drive_until_target(dropoff_odometer_target)

    # === DROPOFF STOP ===
    add_non_driving_period(
        status='on_duty_not_driving',
        duration_hours=DROPOFF_DURATION,
        notes='Dropoff stop',
        stop_type='dropoff',
        stop_label='Dropoff Location',
        stop_notes='1 hour dropoff time',
        lat=dropoff_lat,
        lng=dropoff_lng,
    )

    # Finalize last day
    current_day_log.odometer_end = odometer

    # Compute per-day totals
    for dl in day_logs:
        dl.total_driving = round(sum(p.duration for p in dl.periods if p.status == 'driving'), 2)
        dl.total_on_duty = round(sum(p.duration for p in dl.periods if p.status in ('driving', 'on_duty_not_driving')), 2)
        dl.total_off_duty = round(sum(p.duration for p in dl.periods if p.status in ('off_duty', 'sleeper')), 2)

    return stops, day_logs


def stops_to_dict(stops: List[Stop]) -> list:
    return [
        {
            'stop_type': s.stop_type,
            'label': s.label,
            'location': s.location,
            'lat': s.lat,
            'lng': s.lng,
            'arrive_hour': round(s.arrive_hour, 2),
            'depart_hour': round(s.depart_hour, 2),
            'duration_hours': round(s.depart_hour - s.arrive_hour, 2),
            'odometer': round(s.odometer, 1),
            'notes': s.notes,
        }
        for s in stops
    ]


def day_logs_to_dict(day_logs: List[DayLog]) -> list:
    result = []
    for dl in day_logs:
        periods = []
        for p in dl.periods:
            periods.append({
                'status': p.status,
                'start_hour': round(p.start_hour, 4),
                'end_hour': round(p.end_hour, 4),
                'start_hour_of_day': round(p.start_hour % 24, 4),
                'end_hour_of_day': round(p.end_hour % 24, 4),
                'duration': round(p.duration, 4),
                'notes': p.notes,
            })
        result.append({
            'day': dl.day,
            'date_label': dl.date_label,
            'periods': periods,
            'total_driving': dl.total_driving,
            'total_on_duty': dl.total_on_duty,
            'total_off_duty': dl.total_off_duty,
            'odometer_start': round(dl.odometer_start, 1),
            'odometer_end': round(dl.odometer_end, 1),
            'remarks': dl.remarks,
        })
    return result
