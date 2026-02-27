from django.urls import path
from .views import PlanTripView, TripPlanLatestView, TripPlanRecentView

urlpatterns = [
    path('trips/plan/', PlanTripView.as_view(), name='plan-trip'),
    path('trips/plans/latest/', TripPlanLatestView.as_view(), name='trip-plan-latest'),
    path('trips/plans/recent/', TripPlanRecentView.as_view(), name='trip-plan-recent'),
]
