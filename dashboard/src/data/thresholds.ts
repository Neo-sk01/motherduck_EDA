export type MetricStatus = "good" | "watch" | "at-risk";

export type ThresholdMetricId =
  | "reached_an_agent"
  | "missed_call_rate"
  | "right_language_routing";

interface HigherIsBetter {
  direction: "higher-is-better";
  good: number;
  watch: number;
}

interface LowerIsBetter {
  direction: "lower-is-better";
  good: number;
  watch: number;
}

type ThresholdRule = HigherIsBetter | LowerIsBetter;

const THRESHOLDS: Record<ThresholdMetricId, ThresholdRule> = {
  reached_an_agent: { direction: "higher-is-better", good: 0.9, watch: 0.8 },
  missed_call_rate: { direction: "lower-is-better", good: 0.05, watch: 0.1 },
  right_language_routing: { direction: "higher-is-better", good: 0.95, watch: 0.85 },
};

export function statusFor(metricId: string, value: number): MetricStatus | undefined {
  const rule = THRESHOLDS[metricId as ThresholdMetricId];
  if (!rule) return undefined;
  if (rule.direction === "higher-is-better") {
    if (value >= rule.good) return "good";
    if (value >= rule.watch) return "watch";
    return "at-risk";
  }
  if (value <= rule.good) return "good";
  if (value <= rule.watch) return "watch";
  return "at-risk";
}
