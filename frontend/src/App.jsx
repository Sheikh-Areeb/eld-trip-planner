import { useEffect, useState } from "react";
import InputForm from "./components/InputForm";
import MapView from "./components/MapView";
import ELDLogPage from "./components/ELDLogPage";
import {
  fetchLatestTripPlan,
  fetchRecentTripPlans,
  planTrip,
} from "./services/tripService";
import "./index.css";

const FORM_STORAGE_KEY = "spotter-form-v1";

const TABS = [
  { id: "map", label: "Route Map", icon: "🗺️" },
  { id: "eld", label: "ELD Logs", icon: "📋" },
];

function isCoordinatePair(value) {
  const parts = (value || "").split(",").map((p) => p.trim());
  if (parts.length !== 2) return false;
  const lat = Number(parts[0]);
  const lng = Number(parts[1]);
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180
  );
}

export default function App() {
  const [form, setForm] = useState(() => {
    try {
      const saved = localStorage.getItem(FORM_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          currentLocation: parsed.currentLocation || "",
          pickupLocation: parsed.pickupLocation || "",
          dropoffLocation: parsed.dropoffLocation || "",
          currentCycleUsed: parsed.currentCycleUsed || "",
        };
      }
    } catch {
      // Ignore malformed persisted form data.
    }
    return {
      currentLocation: "",
      pickupLocation: "",
      dropoffLocation: "",
      currentCycleUsed: "",
    };
  });
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState(null);
  const [tripData, setTripData] = useState(null);
  const [tripPlans, setTripPlans] = useState([]);
  const [activeTab, setActiveTab] = useState("map");
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem("spotter-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("spotter-theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(FORM_STORAGE_KEY, JSON.stringify(form));
  }, [form]);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialState() {
      try {
        const recent = await fetchRecentTripPlans(10).catch(() => []);
        if (cancelled) return;
        if (recent.length) {
          setTripPlans(recent);
          setTripData(recent[0]);
          return;
        }
        const latest = await fetchLatestTripPlan().catch(() => null);
        if (cancelled) return;
        if (latest) {
          setTripData(latest);
          setTripPlans([latest]);
        }
      } finally {
        if (!cancelled) setInitializing(false);
      }
    }

    loadInitialState();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleFormChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (error) setError(null);
  };

  const handleSubmit = async () => {
    if (loading) return;
    const { currentLocation, pickupLocation, dropoffLocation } = form;
    const cycleUsedRaw = form.currentCycleUsed?.toString().trim();
    const cycleUsed =
      cycleUsedRaw === "" ? 0 : Number.parseFloat(cycleUsedRaw);

    if (
      !currentLocation.trim() ||
      !pickupLocation.trim() ||
      !dropoffLocation.trim()
    ) {
      setError("Please fill in all three locations.");
      return;
    }
    if (
      !isCoordinatePair(currentLocation) ||
      !isCoordinatePair(pickupLocation) ||
      !isCoordinatePair(dropoffLocation)
    ) {
      setError("Use coordinates in 'lat,lng' format for all three locations.");
      return;
    }
    if (Number.isNaN(cycleUsed) || cycleUsed < 0 || cycleUsed > 70) {
      setError("Current Cycle Used must be a number between 0 and 70.");
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const data = await planTrip(form);
      setTripData(data);
      setTripPlans((prev) => {
        const deduped = prev.filter((p) => p.plan_id !== data.plan_id);
        return [data, ...deduped].slice(0, 10);
      });
      setActiveTab("map");
    } catch (err) {
      let msg = "Unable to plan this trip right now. Please try again.";
      if (err?.code === "ECONNABORTED") {
        msg = "Request timed out. Please try again.";
      } else if (!err?.response) {
        msg = "Cannot reach the server. Check your connection and API URL.";
      } else if (err?.response?.data?.error) {
        msg = err.response.data.error;
      } else if (typeof err?.message === "string") {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="logo-mark">🚛</div>
        <h1>Spotter ELD Trip Planner</h1>
        <button
          className="theme-toggle"
          onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
          type="button"
        >
          {theme === "dark" ? "Light" : "Dark"} Mode
        </button>
        <span className="header-badge">70hr / 8-Day</span>
      </header>

      {/* Main layout */}
      <div className="main-layout">
        {/* Left sidebar */}
        <InputForm
          form={form}
          onFormChange={handleFormChange}
          onSubmit={handleSubmit}
          loading={loading || initializing}
          error={error}
          tripData={tripData}
        />

        {/* Right content */}
        <div className="content-area">
          <div className="tab-bar">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`tab-btn${activeTab === tab.id ? " active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span>{tab.icon}</span>
                {tab.label}
                {tab.id === "eld" && tripPlans.length > 0 && (
                  <span className="tab-count-badge">
                    {tripPlans.length}
                  </span>
                )}
              </button>
            ))}
          </div>

          <div className="tab-content">
            {activeTab === "map" && (
              <div style={{ height: "100%" }}>
                <MapView tripData={tripData} theme={theme} />
              </div>
            )}
            {activeTab === "eld" && (
              <ELDLogPage
                tripData={tripData}
                tripPlans={tripPlans}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
