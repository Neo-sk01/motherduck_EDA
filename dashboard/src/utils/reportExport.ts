import type {
  Anomaly,
  DashboardReport,
  QueueId,
  QueueMetrics,
  SourceGap,
} from "../data/reportTypes";
import { QUEUE_META, QUEUE_ORDER } from "../data/reportTypes";
import { downloadCsv, toCsv } from "./exportCsv";

interface ReportExportRow extends Record<string, unknown> {
  period: string;
  date_start: string;
  date_end: string;
  section: string;
  queue_id: string;
  queue_name: string;
  language: string;
  role: string;
  entity_type: string;
  entity: string;
  date: string;
  hour: string | number;
  dow: string;
  metric: string;
  value: string | number;
  details: string;
}

const EXPORT_COLUMNS = [
  { key: "period", header: "period" },
  { key: "date_start", header: "date_start" },
  { key: "date_end", header: "date_end" },
  { key: "section", header: "section" },
  { key: "queue_id", header: "queue_id" },
  { key: "queue_name", header: "queue_name" },
  { key: "language", header: "language" },
  { key: "role", header: "role" },
  { key: "entity_type", header: "entity_type" },
  { key: "entity", header: "entity" },
  { key: "date", header: "date" },
  { key: "hour", header: "hour" },
  { key: "dow", header: "dow" },
  { key: "metric", header: "metric" },
  { key: "value", header: "value" },
  { key: "details", header: "details" },
] satisfies Array<{ key: keyof ReportExportRow; header: string }>;

export function buildFullReportCsv(report: DashboardReport): string {
  return toCsv(buildFullReportRows(report), EXPORT_COLUMNS);
}

export function buildReportCsvFilename(report: DashboardReport): string {
  return `neolore-queue-analytics-${report.date_range.start}_${report.date_range.end}.csv`;
}

export function downloadFullReportCsv(report: DashboardReport): void {
  downloadCsv(buildReportCsvFilename(report), buildFullReportCsv(report));
}

function buildFullReportRows(report: DashboardReport): ReportExportRow[] {
  const rows: ReportExportRow[] = [];

  pushReportMetadata(rows, report);
  for (const queueId of QUEUE_ORDER) {
    pushQueueRows(rows, report, queueId, report.queues[queueId]);
  }
  pushCrossQueueRows(rows, report);
  for (const anomaly of report.anomalies) pushAnomaly(rows, report, anomaly);
  for (const sourceGap of report.source_gaps) pushSourceGap(rows, report, sourceGap);

  return rows;
}

function pushReportMetadata(rows: ReportExportRow[], report: DashboardReport): void {
  pushMetric(rows, report, "report_metadata", "report", "generated_at", report.generated_at ?? "");
  for (const [key, value] of Object.entries(report.validation)) {
    if (key === "queue_counts") continue;
    pushMetric(rows, report, "report_validation", "validation", key, formatValue(value));
  }
  pushQueueValidationRows(rows, report);
}

function pushQueueValidationRows(rows: ReportExportRow[], report: DashboardReport): void {
  const queueCounts = report.validation.queue_counts;
  if (!queueCounts || typeof queueCounts !== "object") return;
  for (const [queueId, counts] of Object.entries(queueCounts as Record<string, Record<string, unknown>>)) {
    for (const [metric, value] of Object.entries(counts)) {
      pushMetric(rows, report, "report_validation", "queue_validation", metric, value, {
        queueId: queueId as QueueId,
      });
    }
  }
}

function pushQueueRows(
  rows: ReportExportRow[],
  report: DashboardReport,
  queueId: QueueId,
  metrics: QueueMetrics,
): void {
  for (const metric of [
    "raw_rows",
    "cleaned_calls",
    "duplicate_rows_removed",
    "total_calls",
    "handled_calls",
    "answer_rate",
    "no_agent_calls",
    "no_agent_rate",
    "answered_no_agent_reconciled",
    "dedupe_key",
    "calculation_source",
    "days_with_calls",
    "avg_calls_per_active_day",
  ] as const) {
    if (metrics[metric] !== undefined) {
      pushMetric(rows, report, "queue_summary", "queue", metric, metrics[metric], { queueId });
    }
  }

  if (metrics.busiest_day) {
    pushMetric(rows, report, "queue_summary", "queue", "busiest_day_calls", metrics.busiest_day.calls, {
      date: metrics.busiest_day.date,
      queueId,
    });
  }
  if (metrics.quietest_day) {
    pushMetric(rows, report, "queue_summary", "queue", "quietest_day_calls", metrics.quietest_day.calls, {
      date: metrics.quietest_day.date,
      queueId,
    });
  }

  for (const point of metrics.daily_volume) {
    pushMetric(rows, report, "queue_daily_volume", "date", "calls", point.calls, {
      date: point.date,
      entity: point.date,
      queueId,
    });
  }
  for (const point of metrics.weekly_volume ?? []) {
    pushMetric(rows, report, "queue_weekly_volume", "week", "calls", point.calls, {
      entity: `${point.week_start} to ${point.week_end}`,
      queueId,
    });
  }
  for (const point of metrics.hourly_volume) {
    pushMetric(rows, report, "queue_hourly_volume", "hour", "calls", point.calls, {
      hour: point.hour,
      entity: formatHour(point.hour),
      queueId,
    });
    pushMetric(rows, report, "queue_hourly_volume", "hour", "no_answer_count", point.no_answer_count, {
      hour: point.hour,
      entity: formatHour(point.hour),
      queueId,
    });
    pushMetric(rows, report, "queue_hourly_volume", "hour", "no_answer_rate", point.no_answer_rate, {
      hour: point.hour,
      entity: formatHour(point.hour),
      queueId,
    });
    if (point.avg_agent_sec !== undefined) {
      pushMetric(rows, report, "queue_hourly_volume", "hour", "avg_agent_sec", point.avg_agent_sec ?? "", {
        hour: point.hour,
        entity: formatHour(point.hour),
        queueId,
      });
    }
  }
  for (const point of metrics.dow_volume) {
    pushMetric(rows, report, "queue_dow_volume", "day_of_week", "calls", point.calls, {
      dow: point.dow,
      entity: point.dow,
      queueId,
    });
    pushMetric(rows, report, "queue_dow_volume", "day_of_week", "avg_calls_per_occurrence", averageForDow(report, point.dow, point.calls), {
      dow: point.dow,
      entity: point.dow,
      queueId,
    });
  }
  for (const reason of metrics.release_reasons.queue) {
    pushMetric(rows, report, "queue_release_reasons", "queue_reason", "calls", reason.calls, {
      entity: reason.reason,
      queueId,
    });
  }
  for (const reason of metrics.release_reasons.agent) {
    pushMetric(rows, report, "agent_release_reasons", "agent_reason", "calls", reason.calls, {
      entity: reason.reason,
      queueId,
    });
  }
  for (const agent of metrics.agent_leaderboard) {
    for (const metric of ["calls", "avg_sec", "median_sec", "total_sec", "pct_of_answered"] as const) {
      pushMetric(rows, report, "queue_agent_leaderboard", "agent", metric, agent[metric] ?? "", {
        entity: agent.agent_name,
        queueId,
      });
    }
  }
  for (const caller of metrics.top_callers) {
    pushMetric(rows, report, "queue_top_callers", "caller", "calls", caller.calls, {
      entity: caller.caller_number_norm,
      queueId,
    });
  }
  if (metrics.api_stats) {
    for (const [metric, value] of Object.entries(metrics.api_stats)) {
      pushMetric(rows, report, "api_queue_stats_diagnostic", "queue", metric, value, { queueId });
    }
  }
}

function pushCrossQueueRows(rows: ReportExportRow[], report: DashboardReport): void {
  for (const [language, funnel] of Object.entries(report.crossqueue.funnels)) {
    const scopeDetails = [
      language === "English" ? "primary=8020; overflow=8030" : "primary=8021; overflow=8031",
      funnel.drop_definition ? `drop_definition=${funnel.drop_definition}` : "",
      funnel.final_dropped_available === false ? "final dropped unavailable without overflow data" : "",
    ]
      .filter(Boolean)
      .join("; ");
    for (const [metric, value] of Object.entries(funnel)) {
      pushMetric(rows, report, "crossqueue_funnel", "language", metric, value, {
        entity: language,
        details: scopeDetails,
      });
    }
  }

  for (const agent of report.crossqueue.agents) {
    pushMetric(rows, report, "crossqueue_agents", "agent", "total_calls", agent.total_calls, {
      entity: agent.agent_name,
    });
    for (const queueId of QUEUE_ORDER) {
      pushMetric(rows, report, "crossqueue_agents", "agent", "queue_calls", Number(agent[queueId] ?? 0), {
        entity: agent.agent_name,
        queueId,
      });
    }
  }

  for (const caller of report.crossqueue.callers) {
    pushMetric(rows, report, "crossqueue_callers", "caller", "total_calls", caller.total_calls, {
      entity: caller.caller_number_norm,
    });
    for (const queueId of QUEUE_ORDER) {
      pushMetric(rows, report, "crossqueue_callers", "caller", "queue_calls", Number(caller[queueId] ?? 0), {
        entity: caller.caller_number_norm,
        queueId,
      });
    }
  }

  for (const point of report.crossqueue.same_hour_no_answer) {
    pushMetric(rows, report, "crossqueue_same_hour_no_answer", "hour", "calls", point.calls, {
      hour: point.hour,
      entity: formatHour(point.hour),
      queueId: point.queue_id,
    });
    pushMetric(rows, report, "crossqueue_same_hour_no_answer", "hour", "no_answer_count", point.no_answer_count, {
      hour: point.hour,
      entity: formatHour(point.hour),
      queueId: point.queue_id,
    });
    pushMetric(rows, report, "crossqueue_same_hour_no_answer", "hour", "no_answer_rate", point.no_answer_rate, {
      hour: point.hour,
      entity: formatHour(point.hour),
      queueId: point.queue_id,
    });
  }

  for (const point of report.crossqueue.same_day_volume) {
    pushMetric(rows, report, "crossqueue_same_day_volume", "date", "calls", point.calls, {
      date: point.date,
      entity: point.date,
      queueId: point.queue_id,
    });
  }

  for (const [language, funnel] of Object.entries(report.crossqueue.api_stats_funnels ?? {})) {
    for (const [metric, value] of Object.entries(funnel)) {
      pushMetric(rows, report, "api_stats_funnel_diagnostic", "language", metric, value, {
        entity: language,
        details: language === "English" ? "primary=8020; overflow=8030" : "primary=8021; overflow=8031",
      });
    }
  }
}

function pushAnomaly(rows: ReportExportRow[], report: DashboardReport, anomaly: Anomaly): void {
  pushMetric(rows, report, "anomalies", anomaly.kind, "severity", anomaly.severity, {
    details: anomaly.description,
    entity: anomaly.target ? JSON.stringify(anomaly.target) : "",
    queueId: anomaly.queue_id,
  });
}

function pushSourceGap(rows: ReportExportRow[], report: DashboardReport, sourceGap: SourceGap): void {
  pushMetric(rows, report, "source_gaps", "source_gap", sourceGap.reason, sourceGap.message ?? "", {
    queueId: sourceGap.queue_id,
  });
}

function pushMetric(
  rows: ReportExportRow[],
  report: DashboardReport,
  section: string,
  entityType: string,
  metric: string,
  value: unknown,
  options: {
    queueId?: QueueId;
    entity?: string;
    date?: string;
    hour?: number | string;
    dow?: string;
    details?: string;
  } = {},
): void {
  rows.push({
    ...baseRow(report, options.queueId),
    section,
    entity_type: entityType,
    entity: options.entity ?? "",
    date: options.date ?? "",
    hour: options.hour ?? "",
    dow: options.dow ?? "",
    metric,
    value: formatValue(value),
    details: options.details ?? "",
  });
}

function baseRow(report: DashboardReport, queueId?: QueueId): ReportExportRow {
  const meta = queueId ? QUEUE_META[queueId] : null;
  return {
    period: report.period,
    date_start: report.date_range.start,
    date_end: report.date_range.end,
    section: "",
    queue_id: queueId ?? "",
    queue_name: meta?.name ?? "",
    language: meta?.language ?? "",
    role: meta?.role ?? "",
    entity_type: "",
    entity: "",
    date: "",
    hour: "",
    dow: "",
    metric: "",
    value: "",
    details: "",
  };
}

function formatHour(hour: number): string {
  return `${String(hour).padStart(2, "0")}:00`;
}

function averageForDow(report: DashboardReport, dow: string, calls: number): number | string {
  const occurrences = weekdayOccurrences(report.date_range.start, report.date_range.end, dow);
  return occurrences ? calls / occurrences : "";
}

function weekdayOccurrences(start: string, end: string, dow: string): number {
  const target = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"].indexOf(dow);
  if (target < 0) return 0;
  const cursor = new Date(`${start}T00:00:00Z`);
  const endDate = new Date(`${end}T00:00:00Z`);
  let count = 0;
  while (cursor <= endDate) {
    if (cursor.getUTCDay() === target) count += 1;
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return count;
}

function formatValue(value: unknown): string | number {
  if (typeof value === "number" || typeof value === "string") return value;
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}
