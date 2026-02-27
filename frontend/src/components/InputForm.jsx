import { getStopIcon } from "../constants/stops";
import { formatTripTime } from "../utils/time";

export default function InputForm({
  onFormChange,
  onSubmit,
  form,
  loading,
  error,
  tripData,
}) {
  return (
    <div className="sidebar">
      <div className="sidebar-inner">
        <div className="welcome-card">
          <h3>⚡ ELD Trip Planner</h3>
          <ul>
            <li>Property-carrying, 70hr/8-day assumptions</li>
            <li>Fuel stop at least every 1,000 miles</li>
            <li>1 hour pickup and 1 hour dropoff handling time</li>
          </ul>
        </div>

        <div className="card">
          <div className="card-title">
            <span className="icon">🗺</span>Trip Details
          </div>

          <div className="form-group">
            <label>
              <span className="label-dot label-dot-current" />
              Current Location
            </label>
            <input
              type="text"
              placeholder="e.g. Chicago, IL or CHI"
              value={form.currentLocation}
              onChange={(e) => onFormChange("currentLocation", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>
              <span className="label-dot label-dot-pickup" />
              Pickup Location
            </label>
            <input
              type="text"
              placeholder="e.g. Indianapolis, IN or IND"
              value={form.pickupLocation}
              onChange={(e) => onFormChange("pickupLocation", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>
              <span className="label-dot label-dot-dropoff" />
              Dropoff Location
            </label>
            <input
              type="text"
              placeholder="e.g. Nashville, TN or BNA"
              value={form.dropoffLocation}
              onChange={(e) => onFormChange("dropoffLocation", e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>
              <span className="label-dot label-dot-cycle" />
              Current Cycle Used (hrs)
            </label>
            <div className="cycle-row">
              <input
                type="number"
                placeholder="0"
                min="0"
                max="70"
                step="0.5"
                value={form.currentCycleUsed}
                onChange={(e) => onFormChange("currentCycleUsed", e.target.value)}
              />
              <span className="cycle-badge">/ 70 hrs</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <span className="icon">📋</span>HOS Rules Applied
          </div>
          <div className="hos-tags">
            <span className="hos-tag">70hr / 8-Day Cycle</span>
            <span className="hos-tag">14hr Window</span>
            <span className="hos-tag">11hr Drive Limit</span>
            <span className="hos-tag">30-Min Break @ 8hrs</span>
            <span className="hos-tag">10hr Rest Required</span>
            <span className="hos-tag">Fuel @ 1,000mi</span>
            <span className="hos-tag">1hr Pickup / Dropoff</span>
          </div>
        </div>

        {error && (
          <div className="error-banner" role="alert" aria-live="assertive">
            <span className="err-icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <button className="btn-primary" onClick={onSubmit} disabled={loading}>
          {loading ? (
            <>
              <span className="spinner" /> Calculating Route…
            </>
          ) : (
            <>🚀 Plan My Trip</>
          )}
        </button>

        {tripData && <TripSummaryCard tripData={tripData} />}
      </div>
    </div>
  );
}

function TripSummaryCard({ tripData }) {
  const { trip, stops, eld_logs } = tripData;
  const fuelStops = stops.filter((s) => s.stop_type === "fuel").length;
  const restStops = stops.filter((s) => s.stop_type === "rest").length;
  const sheetEndHour =
    Number.isFinite(Number(trip?.num_days)) && Number(trip.num_days) > 0
      ? Number(trip.num_days) * 24
      : Math.max(...stops.map((s) => Number(s.depart_hour) || 0), 24);
  const timelineStops = [
    {
      stop_type: "sheet_start",
      label: "Daily Log Sheet Start",
      arrive_hour: 0,
      depart_hour: 0,
      duration_hours: 0,
      odometer: 0,
      notes: "Day 1 begins at 00:00",
    },
    ...stops,
    {
      stop_type: "sheet_end",
      label: "Daily Log Sheet End",
      arrive_hour: sheetEndHour,
      depart_hour: sheetEndHour,
      duration_hours: 0,
      odometer: trip?.total_distance_miles || 0,
      notes: `Sheets recorded through Day ${eld_logs?.length || trip?.num_days || 1}`,
    },
  ];

  return (
    <>
      <div className="card">
        <div className="card-title">
          <span className="icon">📊</span>Trip Summary
        </div>
        <div className="stats-grid">
          <div className="stat-item">
            <div className="stat-value text-accent">
              {trip.total_distance_miles.toLocaleString()}
            </div>
            <div className="stat-label">Total Miles</div>
          </div>
          <div className="stat-item">
            <div className="stat-value text-success">{trip.num_days}</div>
            <div className="stat-label">Days</div>
          </div>
          <div className="stat-item">
            <div className="stat-value text-warning">{fuelStops}</div>
            <div className="stat-label">Fuel Stops</div>
          </div>
          <div className="stat-item">
            <div className="stat-value text-rest">
              {restStops}
            </div>
            <div className="stat-label">Rest Stops</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">
          <span className="icon">📍</span>Stops & Rests Along Route
        </div>
        <div className="stop-list">
          {timelineStops.map((stop, i) => (
            <div key={i} className="stop-item">
              <div className={`stop-icon ${stop.stop_type}`}>
                {getStopIcon(stop.stop_type)}
              </div>
              <div className="stop-body">
                <div className="stop-label">{stop.label}</div>
                <div className="stop-meta">
                  Arrive {formatTripTime(stop.arrive_hour)}
                  {" · "}
                  Depart {formatTripTime(stop.depart_hour)}
                  {stop.duration_hours > 0 &&
                    ` · ${stop.duration_hours.toFixed(1)}h stop`}
                  {stop.odometer > 0 && ` · mi ${stop.odometer.toLocaleString()}`}
                  {stop.notes ? ` · ${stop.notes}` : ""}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
