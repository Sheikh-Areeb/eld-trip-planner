export function formatTripTime(absHour, separator = ", ") {
  const numeric = Number(absHour) || 0;
  const day = Math.floor(numeric / 24) + 1;
  const h = numeric % 24;
  const hh = Math.floor(h).toString().padStart(2, "0");
  const mm = Math.round((h % 1) * 60)
    .toString()
    .padStart(2, "0");
  return `Day ${day}${separator}${hh}:${mm}`;
}

export function formatAbsoluteTime(absHour) {
  return formatTripTime(absHour, " ");
}

export function formatHourLabel(hour) {
  const numeric = Number(hour) || 0;
  if (numeric === 0 || numeric === 24) return "Midnight";
  if (numeric === 12) return "Noon";
  return `${numeric % 12 || 12}${numeric < 12 ? "a" : "p"}`;
}
