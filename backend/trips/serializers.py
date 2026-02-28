from rest_framework import serializers


class TripPlanRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField()
    pickup_location = serializers.CharField()
    dropoff_location = serializers.CharField()
    current_cycle_used = serializers.FloatField(min_value=0, default=0)
    cycle_rule = serializers.ChoiceField(choices=["60_7", "70_8"], default="70_8")
    adverse_driving_conditions = serializers.BooleanField(default=False)
    short_haul_mode = serializers.ChoiceField(
        choices=["none", "cdl_150", "non_cdl_150"],
        default="none",
    )
    use_16_hour_exception = serializers.BooleanField(default=False)
    used_16_hour_in_last_7_days = serializers.BooleanField(default=False)
    return_to_reporting_location = serializers.BooleanField(default=True)
    enable_34h_restart = serializers.BooleanField(default=True)

    @staticmethod
    def _parse_coordinate_pair(raw_value: str, field_name: str):
        value = (raw_value or "").strip()
        parts = [p.strip() for p in value.split(",")]
        if len(parts) != 2:
            raise serializers.ValidationError(
                f"{field_name} must be in 'lat,lng' format (example: 41.8781,-87.6298)."
            )

        try:
            lat = float(parts[0])
            lng = float(parts[1])
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                f"{field_name} has invalid coordinates. Use numeric 'lat,lng'."
            ) from exc

        if lat < -90 or lat > 90 or lng < -180 or lng > 180:
            raise serializers.ValidationError(
                f"{field_name} coordinates out of range (lat -90..90, lng -180..180)."
            )

        return {"lat": lat, "lng": lng, "label": ""}

    def validate_current_location(self, value):
        self._parse_coordinate_pair(value, "current_location")
        return value.strip()

    def validate_pickup_location(self, value):
        self._parse_coordinate_pair(value, "pickup_location")
        return value.strip()

    def validate_dropoff_location(self, value):
        self._parse_coordinate_pair(value, "dropoff_location")
        return value.strip()

    def validate(self, attrs):
        cycle_rule = attrs["cycle_rule"]
        cycle_max = 60 if cycle_rule == "60_7" else 70
        if attrs["current_cycle_used"] > cycle_max:
            raise serializers.ValidationError(
                {
                    "current_cycle_used": (
                        f"Must be between 0 and {cycle_max} for cycle_rule={cycle_rule}."
                    )
                }
            )

        if attrs["short_haul_mode"] == "non_cdl_150" and attrs["use_16_hour_exception"]:
            raise serializers.ValidationError(
                {
                    "use_16_hour_exception": (
                        "16-hour exception cannot be combined with non_cdl_150 short-haul mode."
                    )
                }
            )
        return attrs

    @classmethod
    def to_trip_point(cls, raw_value: str, field_name: str):
        return cls._parse_coordinate_pair(raw_value, field_name)
