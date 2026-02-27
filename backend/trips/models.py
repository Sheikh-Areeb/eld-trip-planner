from django.db import models


class TripPlan(models.Model):
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used = models.FloatField(default=0.0)
    response_payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.current_location} -> {self.pickup_location} -> "
            f"{self.dropoff_location} ({self.created_at:%Y-%m-%d %H:%M})"
        )
