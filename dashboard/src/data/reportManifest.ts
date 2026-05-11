import { DEFAULT_REPORT_PATH } from "./reportLoader";

export interface ReportOption {
  key: string;
  label: string;
  start: string;
  end: string;
  path: string;
  source: string;
}

interface ManifestPayload {
  reports?: unknown;
}

export const MANIFEST_PATH = "/data/reports/manifest.json";

export const DEFAULT_REPORT_OPTION: ReportOption = {
  key: "2026-04",
  label: "April 2026",
  start: "2026-04-01",
  end: "2026-04-30",
  path: DEFAULT_REPORT_PATH,
  source: "excel_reference_overlay",
};

export function buildReportPath(start: string, end: string): string {
  return `/data/reports/month_${start}_${end}/metrics.json`;
}

export async function loadReportManifest(path = MANIFEST_PATH): Promise<ReportOption[]> {
  try {
    if (typeof fetch !== "function") {
      throw new Error("Fetch is not available in this environment.");
    }
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Manifest request failed with HTTP ${response.status}.`);
    }
    const payload = (await response.json()) as ManifestPayload;
    const reports = Array.isArray(payload.reports) ? payload.reports : [];
    const options = reports.map(validateReportOption);
    return options.length > 0 ? sortReportOptions(options) : [DEFAULT_REPORT_OPTION];
  } catch {
    return [DEFAULT_REPORT_OPTION];
  }
}

export function sortReportOptions(options: ReportOption[]): ReportOption[] {
  return [...options].sort((a, b) => b.start.localeCompare(a.start));
}

function validateReportOption(value: unknown): ReportOption {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Report manifest entry must be an object.");
  }
  const record = value as Record<string, unknown>;
  return {
    key: requireString(record.key, "key"),
    label: requireString(record.label, "label"),
    start: requireString(record.start, "start"),
    end: requireString(record.end, "end"),
    path: requireString(record.path, "path"),
    source: requireString(record.source, "source"),
  };
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Report manifest ${field} must be a string.`);
  }
  return value;
}
