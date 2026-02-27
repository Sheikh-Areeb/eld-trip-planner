import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
  headers: { "Content-Type": "application/json" },
});

export async function planTrip({
  currentLocation,
  pickupLocation,
  dropoffLocation,
  currentCycleUsed,
}) {
  const resp = await api.post("/trips/plan/", {
    current_location: currentLocation,
    pickup_location: pickupLocation,
    dropoff_location: dropoffLocation,
    current_cycle_used: parseFloat(currentCycleUsed) || 0,
    cycle_rule: "70_8",
    adverse_driving_conditions: false,
    short_haul_mode: "none",
    use_16_hour_exception: false,
    used_16_hour_in_last_7_days: false,
    return_to_reporting_location: true,
    enable_34h_restart: true,
  });
  return resp.data;
}

export async function fetchLatestTripPlan() {
  const resp = await api.get("/trips/plans/latest/");
  return resp.data;
}

export async function fetchRecentTripPlans(limit = 5) {
  const resp = await api.get("/trips/plans/recent/", { params: { limit } });
  return resp.data?.plans || [];
}
