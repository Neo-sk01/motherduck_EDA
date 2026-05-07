export function formatInteger(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "0";
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatDecimal(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "0.0";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "0.0%";
  return `${formatDecimal(value * 100, digits)}%`;
}

export function formatHour(hour: number | null | undefined): string {
  if (typeof hour !== "number" || Number.isNaN(hour)) return "n/a";
  return `${String(hour).padStart(2, "0")}:00`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (typeof seconds !== "number" || Number.isNaN(seconds)) return "n/a";
  const totalSeconds = Math.round(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  const remainder = totalSeconds % 60;
  if (minutes <= 0) return `${remainder}s`;
  return `${minutes}m ${String(remainder).padStart(2, "0")}s`;
}

export function formatDateLabel(date: string): string {
  const [year, month, day] = date.split("-").map(Number);
  const parsed = new Date(year, month - 1, day);
  return parsed.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function titleCase(value: string): string {
  return value
    .split("_")
    .join(" ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
