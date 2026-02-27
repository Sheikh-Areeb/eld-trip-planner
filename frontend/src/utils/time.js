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
