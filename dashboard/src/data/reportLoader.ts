import fixtureReport from "../fixtures/april-2026-metrics.json";
import type { DashboardReport, QueueId, ReportLoadResult } from "./reportTypes";
import { QUEUE_ORDER } from "./reportTypes";

interface ImportMetaEnvLike {
  VITE_REPORTS_BASE_URL?: string;
  VITE_ENABLE_FIXTURE_FALLBACK?: string;
  DEV?: boolean;
}

function resolveBase(env: ImportMetaEnvLike = import.meta.env as ImportMetaEnvLike): string {
  const raw = env.VITE_REPORTS_BASE_URL;
  if (typeof raw === "string" && raw.length > 0) return raw.replace(/\/+$/, "");
  return "/data/reports";
}

export const DEFAULT_REPORT_PATH = `${resolveBase()}/month_2026-04-01_2026-04-30/metrics.json`;

export class ReportValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ReportValidationError";
  }
}

export function validateReport(value: unknown): DashboardReport {
  const report = requireRecord(value, "report");
  requireString(report.period, "period");
  const dateRange = requireRecord(report.date_range, "date_range");
  requireString(dateRange.start, "date_range.start");
  requireString(dateRange.end, "date_range.end");

  const queues = requireRecord(report.queues, "queues");
  for (const queueId of QUEUE_ORDER) {
    const queue = requireRecord(queues[queueId], `queues.${queueId}`);
    requireNumber(queue.total_calls, `queues.${queueId}.total_calls`);
    requireArray(queue.daily_volume, `queues.${queueId}.daily_volume`);
    requireArray(queue.hourly_volume, `queues.${queueId}.hourly_volume`);
    requireArray(queue.agent_leaderboard, `queues.${queueId}.agent_leaderboard`);
    requireArray(queue.top_callers, `queues.${queueId}.top_callers`);
  }

  const crossqueue = requireRecord(report.crossqueue, "crossqueue");
  const funnels = requireRecord(crossqueue.funnels, "crossqueue.funnels");
  for (const language of ["English", "French"] as const) {
    const funnel = requireRecord(funnels[language], `crossqueue.funnels.${language}`);
    requireNumber(funnel.routing_match, `crossqueue.funnels.${language}.routing_match`);
    requireNumber(
      funnel.effective_answer_rate,
      `crossqueue.funnels.${language}.effective_answer_rate`,
    );
  }
  requireArray(crossqueue.agents, "crossqueue.agents");
  requireArray(crossqueue.callers, "crossqueue.callers");
  requireArray(crossqueue.same_hour_no_answer, "crossqueue.same_hour_no_answer");
  requireArray(crossqueue.same_day_volume, "crossqueue.same_day_volume");
  requireArray(report.anomalies, "anomalies");
  requireArray(report.source_gaps, "source_gaps");
  requireRecord(report.validation, "validation");

  return report as unknown as DashboardReport;
}

export async function loadReport(options?: {
  path?: string;
  useFixtureFallback?: boolean;
  env?: ImportMetaEnvLike;
}): Promise<ReportLoadResult> {
  const env = options?.env ?? (import.meta.env as ImportMetaEnvLike);
  const path = options?.path ?? DEFAULT_REPORT_PATH;
  const allowFixture = env.DEV === true || env.VITE_ENABLE_FIXTURE_FALLBACK === "true";
  const useFixtureFallback = options?.useFixtureFallback ?? allowFixture;

  try {
    if (typeof fetch !== "function") {
      throw new Error("Fetch is not available in this environment.");
    }
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Report request failed with HTTP ${response.status}.`);
    }
    const json = await response.json();
    return {
      status: "loaded",
      source: "remote",
      path,
      report: validateReport(json),
    };
  } catch (error) {
    if (useFixtureFallback) {
      return {
        status: "loaded",
        source: "fixture",
        path,
        report: validateReport(fixtureReport),
        warning: error instanceof Error ? error.message : "Report fetch failed.",
      };
    }
    return {
      status: "error",
      source: "remote",
      path,
      error: error instanceof Error ? error.message : "Report fetch failed.",
    };
  }
}

function requireRecord(value: unknown, field: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ReportValidationError(`${field} must be an object.`);
  }
  return value as Record<string, unknown>;
}

function requireString(value: unknown, field: string): void {
  if (typeof value !== "string" || value.length === 0) {
    throw new ReportValidationError(`${field} must be a string.`);
  }
}

function requireNumber(value: unknown, field: string): void {
  if (typeof value !== "number" || Number.isNaN(value)) {
    throw new ReportValidationError(`${field} must be a number.`);
  }
}

function requireArray(value: unknown, field: string): void {
  if (!Array.isArray(value)) {
    throw new ReportValidationError(`${field} must be an array.`);
  }
}

export function isQueueId(value: string): value is QueueId {
  return (QUEUE_ORDER as string[]).includes(value);
}
