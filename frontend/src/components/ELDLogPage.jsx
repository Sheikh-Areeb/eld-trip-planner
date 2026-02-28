import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ComposedChart,
} from "recharts";
import { formatAbsoluteTime, formatHourLabel } from "../utils/time";

const STATUS_ROWS = [
  { key: "off_duty", label: "1. Off Duty", color: "#6b7280", level: 0 },
  { key: "sleeper", label: "2. Sleeper Berth", color: "#7c3aed", level: 1 },
  { key: "driving", label: "3. Driving", color: "#059669", level: 2 },
  {
    key: "on_duty_not_driving",
    label: "4. On Duty (Not Driving)",
    color: "#d97706",
    level: 3,
  },
];

const STATUS_BY_KEY = STATUS_ROWS.reduce((acc, row) => {
  acc[row.key] = row;
  return acc;
}, {});

function clampHour(hour) {
  return Math.max(0, Math.min(24, Number(hour) || 0));
}

function normalizePeriods(periods) {
  const normalized = [];

  (periods || []).forEach((period) => {
    const status = STATUS_BY_KEY[period.status] ? period.status : null;
    if (!status) return;

    const start = clampHour(period.start_hour_of_day);
    const end = clampHour(period.end_hour_of_day);

    if (end > start) {
      normalized.push({ start, end, status });
      return;
    }

    if (start < 24) normalized.push({ start, end: 24, status });
    if (end > 0) normalized.push({ start: 0, end, status });
  });

  const sorted = normalized.sort((a, b) => a.start - b.start || a.end - b.end);
  if (!sorted.length) {
    return [{ start: 0, end: 24, status: "off_duty" }];
  }

  const withFullDayCoverage = [];
  let cursor = 0;
  for (const period of sorted) {
    const start = Math.max(cursor, period.start);
    const end = Math.max(start, period.end);

    if (start > cursor) {
      withFullDayCoverage.push({
        start: cursor,
        end: start,
        status: "off_duty",
      });
    }

    if (end > start) {
      withFullDayCoverage.push({
        start,
        end,
        status: period.status,
      });
      cursor = end;
    }
  }

  if (cursor < 24) {
    withFullDayCoverage.push({ start: cursor, end: 24, status: "off_duty" });
  }

  return withFullDayCoverage;
}

function buildChartSeries(periods) {
  if (!periods.length) return [];

  const points = [];
  periods.forEach((period, index) => {
    const level = STATUS_BY_KEY[period.status].level;
    if (index === 0) {
      points.push({ hour: period.start, statusLevel: level, status: period.status });
    }
    points.push({ hour: period.end, statusLevel: level, status: period.status });

    const next = periods[index + 1];
    if (next) {
      points.push({
        hour: next.start,
        statusLevel: STATUS_BY_KEY[next.status].level,
        status: next.status,
      });
    }
  });

  if (points[points.length - 1]?.hour !== 24) {
    const last = points[points.length - 1];
    points.push({ ...last, hour: 24 });
  }

  return points;
}

function totalsFromPeriods(periods) {
  return periods.reduce(
    (acc, period) => {
      const duration = Math.max(0, period.end - period.start);
      acc[period.status] += duration;
      return acc;
    },
    {
      off_duty: 0,
      sleeper: 0,
      driving: 0,
      on_duty_not_driving: 0,
    },
  );
}

function ELDTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const status = STATUS_BY_KEY[payload[0].payload.status];

  return (
    <div className="eld-tooltip eld-tooltip-paper">
      <div className="eld-tooltip-hour">{formatHourLabel(Math.round(label))}</div>
      {status && (
        <div className="eld-tooltip-status" style={{ color: status.color }}>
          {status.label}
        </div>
      )}
    </div>
  );
}

function ELDSheet({ dayLog, trip, cycleUsedBeforeTrip }) {
  const periods = normalizePeriods(dayLog.periods);
  const chartData = buildChartSeries(periods);
  const totals = totalsFromPeriods(periods);
  const totalOnDuty = totals.driving + totals.on_duty_not_driving;
  const dayMiles = Math.max(0, (dayLog.odometer_end || 0) - (dayLog.odometer_start || 0));
  const dayStartAbsHour = Math.min(...(dayLog.periods || []).map((p) => p.start_hour ?? 0), 0);

  const fromLabel = trip?.current_location?.label || "-";
  const toLabel = trip?.dropoff_location?.label || "-";

  return (
    <div className="eld-sheet-paper">
      <div className="eld-paper-top">
        <div>
          <div className="eld-paper-title">Driver&apos;s Daily Log</div>
          <div className="eld-paper-subtitle">(24 hours)</div>
        </div>
        <div className="eld-paper-date">{dayLog.date_label}</div>
      </div>

      <div className="eld-paper-lines">
        <div>From: <span>{fromLabel}</span></div>
        <div>To: <span>{toLabel}</span></div>
      </div>

      <div className="eld-paper-stats">
        <div>Total Miles Driving Today: {dayMiles.toFixed(1)} mi</div>
        <div>Total Driving Time Today: {dayLog.total_driving.toFixed(1)}h</div>
        <div>Carrier: Spotter Logistics</div>
        <div>Cycle Used Before Trip: {cycleUsedBeforeTrip.toFixed(1)}h</div>
        <div>Start Time: {formatAbsoluteTime(dayStartAbsHour)}</div>
      </div>

      <div className="eld-paper-grid-wrap">
        <div className="eld-paper-grid">
          <ResponsiveContainer width="100%" height={250}>
            <ComposedChart
              data={chartData}
              margin={{ top: 16, right: 12, left: 140, bottom: 18 }}
            >
              <CartesianGrid stroke="#d1d5db" strokeDasharray="2 2" />
              <XAxis
                dataKey="hour"
                type="number"
                domain={[0, 24]}
                ticks={[0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]}
                stroke="#374151"
                tick={{ fontSize: 10, fill: "#111827" }}
                tickFormatter={(h) =>
                  h % 6 === 0
                    ? formatHourLabel(h)
                    : `${h % 12 || 12}${h < 12 ? "a" : "p"}`
                }
              />
              <YAxis
                type="number"
                domain={[-0.5, 3.5]}
                ticks={STATUS_ROWS.map((s) => s.level)}
                tickFormatter={(level) =>
                  STATUS_ROWS.find((s) => s.level === level)?.label || ""
                }
                stroke="#374151"
                tick={{ fontSize: 10, fill: "#111827" }}
                width={130}
                reversed
              />
              <Tooltip content={<ELDTooltip />} />

              {periods.map((period, idx) => {
                const status = STATUS_BY_KEY[period.status];
                return (
                  <ReferenceArea
                    key={`${period.status}-${period.start}-${period.end}-${idx}`}
                    x1={period.start}
                    x2={period.end}
                    y1={status.level - 0.38}
                    y2={status.level + 0.38}
                    fill={status.color}
                    fillOpacity={0.2}
                    strokeOpacity={0}
                  />
                );
              })}

              <Line
                type="stepAfter"
                dataKey="statusLevel"
                stroke="#111827"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="eld-paper-totals">
          <div>Off Duty: {totals.off_duty.toFixed(1)}h</div>
          <div>Sleeper: {totals.sleeper.toFixed(1)}h</div>
          <div>Driving: {totals.driving.toFixed(1)}h</div>
          <div>On Duty: {totals.on_duty_not_driving.toFixed(1)}h</div>
          <div className="eld-paper-total-main">Total On Duty: {totalOnDuty.toFixed(1)}h</div>
        </div>
      </div>

    </div>
  );
}

const TIME_FILTERS = [
  { id: "all", label: "All" },
  { id: "24h", label: "24h" },
  { id: "7d", label: "7d" },
  { id: "30d", label: "30d" },
];

function isPlanInWindow(plan, filterId, nowMs) {
  if (filterId === "all") return true;
  const createdAt = plan?.created_at ? new Date(plan.created_at).getTime() : NaN;
  if (!Number.isFinite(createdAt)) return false;

  const hours =
    filterId === "24h" ? 24 : filterId === "7d" ? 24 * 7 : 24 * 30;
  return nowMs - createdAt <= hours * 60 * 60 * 1000;
}

export default function ELDLogPage({ tripData, tripPlans = [] }) {
  const [timeFilter, setTimeFilter] = useState("all");
  const [filterBaseTimeMs] = useState(() => Date.now());
  const plans = useMemo(
    () => (tripPlans.length ? tripPlans : tripData ? [tripData] : []),
    [tripData, tripPlans],
  );
  const filteredPlans = useMemo(
    () => plans.filter((plan) => isPlanInWindow(plan, timeFilter, filterBaseTimeMs)),
    [plans, timeFilter, filterBaseTimeMs],
  );

  if (!plans.length) {
    return (
      <div className="eld-page">
        <div className="empty-state" style={{ minHeight: 400 }}>
          <div className="empty-icon">📋</div>
          <p>ELD Log Sheets will appear here</p>
          <small>Plan a trip to generate daily logs</small>
        </div>
      </div>
    );
  }

  return (
    <div className="eld-page">
      <div className="eld-page-title">
        📋 Driver&apos;s Daily Logs - {plans.length} trip{plans.length !== 1 ? "s" : ""}
      </div>
      <div className="eld-filter-row">
        {TIME_FILTERS.map((filter) => (
          <button
            key={filter.id}
            type="button"
            className={`eld-filter-chip${timeFilter === filter.id ? " active" : ""}`}
            onClick={() => setTimeFilter(filter.id)}
          >
            {filter.label}
          </button>
        ))}
      </div>
      {!filteredPlans.length && (
        <div className="eld-empty-filter">
          No saved trips found for this time filter.
        </div>
      )}
      {filteredPlans.map((plan) => {
        const eldLogs = plan?.eld_logs || [];
        const trip = plan?.trip || {};
        const cycleUsedBeforeTrip = Number.isFinite(Number(trip?.current_cycle_used))
          ? Number(trip.current_cycle_used)
          : 0;
        const createdAt = plan?.created_at
          ? new Date(plan.created_at).toLocaleString()
          : "Unknown time";

        return (
          <section key={plan?.plan_id ?? createdAt} className="eld-trip-section">
            <div className="eld-trip-title">
              Trip #{plan?.plan_id ?? "N/A"} • {createdAt} • {eldLogs.length} day
              {eldLogs.length !== 1 ? "s" : ""}
            </div>
            <div className="eld-sheets-container">
              {eldLogs.map((log, i) => (
                <ELDSheet
                  key={`${plan?.plan_id ?? "plan"}-${i}`}
                  dayLog={log}
                  trip={trip}
                  cycleUsedBeforeTrip={cycleUsedBeforeTrip}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
