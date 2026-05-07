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
