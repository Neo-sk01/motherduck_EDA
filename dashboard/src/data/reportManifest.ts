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

interface ImportMetaEnvLike {
  VITE_REPORTS_BASE_URL?: string;
  VITE_ENABLE_FIXTURE_FALLBACK?: string;
  DEV?: boolean;
}

export function resolveReportsBaseUrl(env: ImportMetaEnvLike = import.meta.env as ImportMetaEnvLike): string {
  const raw = env.VITE_REPORTS_BASE_URL;
  if (typeof raw === "string" && raw.length > 0) {
    return raw.replace(/\/+$/, "");
  }
  return "/data/reports";
}

export const MANIFEST_PATH = `${resolveReportsBaseUrl()}/manifest.json`;

export const DEFAULT_REPORT_OPTION: ReportOption = {
  key: "2026-04",
  label: "April 2026",
  start: "2026-04-01",
  end: "2026-04-30",
  path: DEFAULT_REPORT_PATH,
  source: "excel_reference_overlay",
};

export function buildReportPath(start: string, end: string, env?: ImportMetaEnvLike): string {
  const base = resolveReportsBaseUrl(env);
  return `${base}/month_${start}_${end}/metrics.json`;
}

export async function loadReportManifest(
  path?: string,
  env: ImportMetaEnvLike = import.meta.env as ImportMetaEnvLike,
): Promise<ReportOption[]> {
  const resolvedPath = path ?? `${resolveReportsBaseUrl(env)}/manifest.json`;
  const allowFixture = env.DEV === true || env.VITE_ENABLE_FIXTURE_FALLBACK === "true";
  try {
    if (typeof fetch !== "function") {
      throw new Error("Fetch is not available in this environment.");
    }
    const response = await fetch(resolvedPath, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Manifest request failed with HTTP ${response.status}.`);
    }
    const payload = (await response.json()) as ManifestPayload;
    const reports = Array.isArray(payload.reports) ? payload.reports : [];
    const base = resolveReportsBaseUrl(env);
    const options = reports.map((r) => normalizeReportOption(r, base));
    if (options.length === 0) {
      if (allowFixture) return [DEFAULT_REPORT_OPTION];
      throw new Error("Manifest has no entries.");
    }
    return sortReportOptions(options);
  } catch (err) {
    if (allowFixture) return [DEFAULT_REPORT_OPTION];
    throw err;
  }
}

export function sortReportOptions(options: ReportOption[]): ReportOption[] {
  return [...options].sort((a, b) => b.start.localeCompare(a.start));
}

function normalizeReportOption(value: unknown, base: string): ReportOption {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Report manifest entry must be an object.");
  }
  const record = value as Record<string, unknown>;
  const rawPath = requireString(record.path, "path");
  const resolvedPath = isAbsolute(rawPath) ? rawPath : `${base}/${rawPath}`;
  return {
    key: requireString(record.key, "key"),
    label: requireString(record.label, "label"),
    start: requireString(record.start, "start"),
    end: requireString(record.end, "end"),
    path: resolvedPath,
    source: requireString(record.source, "source"),
  };
}

function isAbsolute(path: string): boolean {
  return path.startsWith("/") || /^https?:\/\//.test(path);
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`Report manifest ${field} must be a string.`);
  }
  return value;
}
