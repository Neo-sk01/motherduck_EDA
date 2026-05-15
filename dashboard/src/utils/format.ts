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

export function formatPhone(value: string): string {
  if (!value) return value;
  const digits = value.replace(/[^\d]/g, "");
  if (digits.length === 11 && digits.startsWith("1")) {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  if (digits.length === 10) {
    return `+1 (${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  return value;
}

const ANOMALY_KIND_LABELS: Record<string, string> = {
  volume_spike: "Volume spike",
  volume_drop: "Volume drop",
  cross_queue_caller: "Caller hit multiple queues",
  no_agent_outlier: "Unusual missed-call rate",
  routing_mismatch: "Wrong-language routing",
};

export function humanizeAnomalyKind(kind: string): string {
  return ANOMALY_KIND_LABELS[kind] ?? titleCase(kind);
}
