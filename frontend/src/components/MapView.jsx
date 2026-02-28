import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { STOP_COLORS, getStopIcon } from "../constants/stops";
import { formatTripTime } from "../utils/time";

const LOCATIONIQ_KEY = import.meta.env.VITE_LOCATIONIQ_KEY || "";
const LOCATIONIQ_TILE_BASE = `https://tiles.locationiq.com/v3`;
const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

// Fix default marker icon paths for Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function createStopIcon(stopType) {
  const color = STOP_COLORS[stopType] || "#94a3b8";
  const emoji = getStopIcon(stopType);
  return L.divIcon({
    html: `
      <div style="
        width:36px;height:36px;border-radius:50%;
        background:${color}22;
        border:2.5px solid ${color};
        display:flex;align-items:center;justify-content:center;
        font-size:16px;
        box-shadow:0 2px 8px ${color}55;
      ">${emoji}</div>
    `,
    className: "",
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -20],
  });
}

function FitBounds({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords && coords.length > 1) {
      const bounds = L.latLngBounds(coords);
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [coords, map]);
  return null;
}

export default function MapView({ tripData, theme = "dark" }) {
  const themeName = theme === "dark" ? "dark" : "light";
  const tileUrl = LOCATIONIQ_KEY
    ? `${LOCATIONIQ_TILE_BASE}/${themeName}/r/{z}/{x}/{y}.png?key=${LOCATIONIQ_KEY}`
    : OSM_TILE_URL;

  if (!tripData) {
    return (
      <div
        className="map-wrapper"
        style={{
          background: "var(--bg-base)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div className="empty-state">
          <div className="empty-icon">🗺️</div>
          <p>Your route will appear here</p>
          <small>Enter trip details and click Plan My Trip</small>
        </div>
      </div>
    );
  }

  const { route, stops, trip } = tripData;
  const allCoords = route.all_coordinates; // [[lat, lng], ...]

  // Only show stops with lat/lng
  const mappableStops = stops.filter((s) => s.lat != null && s.lng != null);

  const center =
    allCoords.length > 0
      ? allCoords[Math.floor(allCoords.length / 2)]
      : [39.5, -98.35];

  return (
    <div className="map-wrapper">
      <MapContainer
        key={tripData?.plan_id || `${trip?.current_location?.label || ""}-${trip?.dropoff_location?.label || ""}`}
        center={center}
        zoom={5}
        style={{ width: "100%", height: "100%" }}
        zoomControl={true}
      >
        <TileLayer
          url={tileUrl}
          attribution={
            LOCATIONIQ_KEY
              ? '&copy; <a href="https://locationiq.com/">LocationIQ</a>'
              : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          }
          maxZoom={19}
        />

        {/* Single-trip route only */}
        {allCoords.length > 1 && (
          <Polyline
            positions={allCoords}
            pathOptions={{ color: "#0f766e", weight: 4, opacity: 0.9 }}
          />
        )}

        {/* Current Location */}
        {trip.current_location?.lat && (
          <Marker
            position={[trip.current_location.lat, trip.current_location.lng]}
            icon={createStopIcon("start")}
          >
            <Popup>
              <div className="popup-title">📍 Current Location</div>
              <div className="popup-body">{trip.current_location.label}</div>
            </Popup>
          </Marker>
        )}

        {/* All computed stops */}
        {mappableStops.map((stop, i) => (
          <Marker
            key={i}
            position={[stop.lat, stop.lng]}
            icon={createStopIcon(stop.stop_type)}
          >
            <Popup>
              <div className="popup-title">
                {getStopIcon(stop.stop_type)} {stop.label}
              </div>
              <div className="popup-body">
                <div>Arrive: {formatTripTime(stop.arrive_hour)}</div>
                <div>Depart: {formatTripTime(stop.depart_hour)}</div>
                {stop.duration_hours > 0 && (
                  <div>Duration: {stop.duration_hours.toFixed(1)}h</div>
                )}
                <div>Odometer: {stop.odometer.toLocaleString()} mi</div>
                {stop.notes && (
                  <div style={{ marginTop: 4, opacity: 0.8 }}>{stop.notes}</div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        <FitBounds coords={allCoords} />
      </MapContainer>
    </div>
  );
}
