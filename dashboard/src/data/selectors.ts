import type {
  ConsolidatedAgent,
  ConsolidatedCaller,
  DashboardReport,
  FunnelMetrics,
  QueueId,
  QueueMetadata,
  QueueMetrics,
  SameDayVolumePoint,
} from "./reportTypes";
import { QUEUE_META, QUEUE_ORDER } from "./reportTypes";

export interface QueueSummary {
  meta: QueueMetadata;
  metrics: QueueMetrics;
  busiestHour: number | null;
  topAgent: string;
  topCaller: string;
}

export function getQueueSummaries(report: DashboardReport): QueueSummary[] {
  return QUEUE_ORDER.map((queueId) => {
    const metrics = report.queues[queueId];
    const busiestHour = [...metrics.hourly_volume].sort(
      (a, b) => b.calls - a.calls || a.hour - b.hour,
    )[0]?.hour ?? null;
    return {
      meta: QUEUE_META[queueId],
      metrics,
      busiestHour,
      topAgent: metrics.agent_leaderboard[0]?.agent_name ?? "n/a",
      topCaller: metrics.top_callers[0]?.caller_number_norm ?? "n/a",
    };
  });
}

export function getLanguageFunnels(report: DashboardReport): Array<{
  language: "English" | "French";
  funnel: FunnelMetrics;
  primaryQueue: QueueId;
  overflowQueue: QueueId;
}> {
  return [
    {
      language: "English",
      funnel: report.crossqueue.funnels.English,
      primaryQueue: "8020",
      overflowQueue: "8030",
    },
    {
      language: "French",
      funnel: report.crossqueue.funnels.French,
      primaryQueue: "8021",
      overflowQueue: "8031",
    },
  ];
}

export function getAgentRows(report: DashboardReport): ConsolidatedAgent[] {
  return [...report.crossqueue.agents].sort(sortByTotalThenName("agent_name"));
}

export function getCallerRows(
  report: DashboardReport,
  options?: { multiQueueOnly?: boolean },
): ConsolidatedCaller[] {
  const rows = [...report.crossqueue.callers].sort(sortByTotalThenName("caller_number_norm"));
  if (!options?.multiQueueOnly) return rows;
  return rows.filter((row) => QUEUE_ORDER.filter((queueId) => Number(row[queueId] ?? 0) > 0).length >= 2);
}

export function getTopAgent(report: DashboardReport): ConsolidatedAgent | undefined {
  return getAgentRows(report)[0];
}

export function getTopCaller(report: DashboardReport): ConsolidatedCaller | undefined {
  return getCallerRows(report)[0];
}

export function normalizeSameDayVolume(points: SameDayVolumePoint[]): SameDayVolumePoint[] {
  const maxByQueue = new Map<QueueId, number>();
  for (const point of points) {
    maxByQueue.set(point.queue_id, Math.max(maxByQueue.get(point.queue_id) ?? 0, point.calls));
  }
  return points.map((point) => ({
    ...point,
    calls: maxByQueue.get(point.queue_id) ? point.calls / (maxByQueue.get(point.queue_id) ?? 1) : 0,
  }));
}

export function queueColumnValue(
  row: ConsolidatedAgent | ConsolidatedCaller,
  queueId: QueueId,
): number {
  return Number(row[queueId] ?? 0);
}

function sortByTotalThenName<T extends { total_calls: number }>(
  nameKey: keyof T,
): (a: T, b: T) => number {
  return (a, b) => b.total_calls - a.total_calls || String(a[nameKey]).localeCompare(String(b[nameKey]));
}

export interface PeriodSummary {
  periodLabel: string;
  totalCalls: number;
  reachedRate: number;
  anomalyCount: number;
  sourceGapCount: number;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/**
 * Headline summary for the Overview view.
 *
 * Note: `totalCalls` sums every queue's `total_calls` (including overflow queues),
 * while `reachedRate` is computed from funnel `primary_calls`. These intentionally
 * use different denominators — `totalCalls` answers "how much traffic moved through
 * the system", and `reachedRate` answers "of calls into the primary queues, how
 * many reached an agent."
 */
export function getPeriodSummary(report: DashboardReport): PeriodSummary {
  const [year, month] = report.date_range.start.split("-").map(Number);
  const periodLabel = `${MONTH_NAMES[month - 1]} ${year}`;

  const totalCalls = Object.values(report.queues).reduce(
    (sum, queue) => sum + (queue.total_calls ?? 0),
    0,
  );

  const funnels = Object.values(report.crossqueue.funnels);
  const primary = funnels.reduce((sum, f) => sum + (f.primary_calls ?? 0), 0);
  const answered = funnels.reduce(
    (sum, f) => sum + (f.primary_answered ?? 0) + (f.overflow_answered ?? 0),
    0,
  );
  const reachedRate = primary > 0 ? answered / primary : 0;

  return {
    periodLabel,
    totalCalls,
    reachedRate,
    anomalyCount: report.anomalies.length,
    sourceGapCount: report.source_gaps.length,
  };
}
