export type QueueId = "8020" | "8021" | "8030" | "8031";
export type QueueRole = "primary" | "overflow";
export type QueueLanguage = "English" | "French";
export type ViewKey = "overview" | "per-queue" | "cross-queue" | "funnel-detail";

export interface QueueMetadata {
  id: QueueId;
  name: string;
  language: QueueLanguage;
  role: QueueRole;
  color: string;
}

export interface QueueDayPoint {
  date: string;
  calls: number;
}

export interface QueueHourPoint {
  hour: number;
  calls: number;
  no_answer_count: number;
  no_answer_rate: number;
  avg_agent_sec?: number | null;
}

export interface QueueDowPoint {
  dow: string;
  calls: number;
}

export interface QueueWeekPoint {
  week_start: string;
  week_end: string;
  calls: number;
}

export interface ReasonCount {
  reason: string;
  calls: number;
}

export interface QueueAgent {
  agent_name: string;
  calls: number;
  avg_sec: number | null;
  median_sec: number | null;
  total_sec: number | null;
  pct_of_answered: number;
}

export interface QueueCaller {
  caller_number_norm: string;
  calls: number;
}

export interface QueueMetrics {
  queue_id: QueueId;
  total_calls: number;
  handled_calls: number;
  no_agent_calls: number;
  answer_rate?: number;
  no_agent_rate: number;
  raw_rows?: number;
  cleaned_calls?: number;
  duplicate_rows_removed?: number;
  answered_no_agent_reconciled?: boolean;
  dedupe_key?: string;
  calculation_source?: string;
  days_with_calls: number;
  avg_calls_per_active_day: number;
  busiest_day: QueueDayPoint | null;
  quietest_day: QueueDayPoint | null;
  daily_volume: QueueDayPoint[];
  weekly_volume?: QueueWeekPoint[];
  hourly_volume: QueueHourPoint[];
  dow_volume: QueueDowPoint[];
  release_reasons: {
    queue: ReasonCount[];
    agent: ReasonCount[];
  };
  agent_leaderboard: QueueAgent[];
  top_callers: QueueCaller[];
  api_stats?: Record<string, unknown>;
}

export interface FunnelMetrics {
  primary_calls: number;
  primary_answered: number;
  primary_failed: number;
  primary_no_agent_calls?: number;
  primary_no_agent_rate?: number;
  overflow_received: number;
  routing_match: number;
  overflow_answered: number;
  overflow_failed: number;
  lost: number;
  lost_rate: number;
  effective_answer_rate: number;
  unaccounted: number;
  final_dropped_available?: boolean;
  final_dropped_calls?: number | null;
  drop_definition?: string;
}

export interface ConsolidatedAgent {
  agent_name: string;
  total_calls: number;
  [queueId: string]: string | number;
}

export interface ConsolidatedCaller {
  caller_number_norm: string;
  total_calls: number;
  [queueId: string]: string | number;
}

export interface SameHourNoAnswerPoint {
  queue_id: QueueId;
  hour: number;
  calls: number;
  no_answer_count: number;
  no_answer_rate: number;
}

export interface SameDayVolumePoint {
  queue_id: QueueId;
  date: string;
  calls: number;
}

export interface Anomaly {
  severity: "low" | "medium" | "high" | string;
  kind: string;
  queue_id?: QueueId;
  description: string;
  target?: {
    view?: string;
    queue_id?: QueueId;
    agent_name?: string;
    hour?: number;
    entity?: string;
  };
}

export interface SourceGap {
  queue_id?: QueueId;
  reason: string;
  message?: string;
}

export interface DashboardReport {
  period: string;
  date_range: {
    start: string;
    end: string;
  };
  generated_at?: string;
  queues: Record<QueueId, QueueMetrics>;
  crossqueue: {
    funnels: Record<QueueLanguage, FunnelMetrics>;
    agents: ConsolidatedAgent[];
    callers: ConsolidatedCaller[];
    same_hour_no_answer: SameHourNoAnswerPoint[];
    same_day_volume: SameDayVolumePoint[];
    api_stats_funnels?: Record<QueueLanguage, FunnelMetrics>;
  };
  anomalies: Anomaly[];
  source_gaps: SourceGap[];
  validation: {
    status?: string;
    [key: string]: unknown;
  };
}

export type ReportLoadResult =
  | {
      status: "loaded";
      source: "remote" | "fixture";
      path: string;
      report: DashboardReport;
      warning?: string;
    }
  | {
      status: "error";
      source: "remote";
      path: string;
      error: string;
    };

export const QUEUE_ORDER: QueueId[] = ["8020", "8021", "8030", "8031"];

export const QUEUE_META: Record<QueueId, QueueMetadata> = {
  "8020": {
    id: "8020",
    name: "CSR English",
    language: "English",
    role: "primary",
    color: "#1F5E2E",
  },
  "8021": {
    id: "8021",
    name: "CSR French",
    language: "French",
    role: "primary",
    color: "#232126",
  },
  "8030": {
    id: "8030",
    name: "CSR Overflow English",
    language: "English",
    role: "overflow",
    color: "#3F8648",
  },
  "8031": {
    id: "8031",
    name: "CSR Overflow French",
    language: "French",
    role: "overflow",
    color: "#6DA66B",
  },
};
