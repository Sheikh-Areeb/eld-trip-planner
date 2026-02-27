export const STOP_ICONS = {
  sheet_start: "🕛",
  sheet_end: "✅",
  start: "📍",
  pickup: "📦",
  dropoff: "🏁",
  fuel: "⛽",
  rest: "🛏",
  break_30: "⏸",
};

export const STOP_COLORS = {
  start: "#14b8a6",
  pickup: "#0f766e",
  dropoff: "#f97316",
  fuel: "#f59e0b",
  rest: "#a16207",
  break_30: "#e11d48",
};

export function getStopIcon(stopType) {
  return STOP_ICONS[stopType] || "●";
}
