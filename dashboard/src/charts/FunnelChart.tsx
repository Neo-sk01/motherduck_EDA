import type { FunnelMetrics, QueueId } from "../data/reportTypes";
import { QUEUE_META } from "../data/reportTypes";
import { formatInteger, formatPercent } from "../utils/format";

interface FunnelChartProps {
  language: "English" | "French";
  funnel: FunnelMetrics;
  primaryQueue: QueueId;
  overflowQueue: QueueId;
}

export function FunnelChart({ language, funnel, primaryQueue, overflowQueue }: FunnelChartProps) {
  const max = Math.max(funnel.primary_calls, 1);
  const steps = [
    {
      label: "Primary calls",
      value: funnel.primary_calls,
      color: QUEUE_META[primaryQueue].color,
    },
    {
      label: "Primary answered",
      value: funnel.primary_answered,
      color: "#2B7A4B",
    },
    {
      label: "Primary failed",
      value: funnel.primary_failed,
      color: "#A32D2D",
    },
    {
      label: "Overflow received",
      value: funnel.overflow_received,
      color: QUEUE_META[overflowQueue].color,
    },
    {
      label: "Overflow answered",
      value: funnel.overflow_answered,
      color: "#2B7A4B",
    },
    {
      label: "Lost",
      value: funnel.lost,
      color: "#A32D2D",
    },
    {
      label: "Unaccounted",
      value: funnel.unaccounted,
      color: "#7B6B3A",
    },
  ];

  return (
    <div className="funnel-chart" aria-label={`${language} routing funnel`}>
      <div className="funnel-rates">
        <span>Routing {formatPercent(funnel.routing_match)}</span>
        <span>Effective {formatPercent(funnel.effective_answer_rate)}</span>
      </div>
      {steps.map((step) => (
        <div className="funnel-row" key={step.label}>
          <span>{step.label}</span>
          <div className="funnel-track">
            <i
              style={{
                width: `${Math.max(5, Math.abs(step.value / max) * 100)}%`,
                backgroundColor: step.color,
              }}
            />
          </div>
          <strong>{formatInteger(step.value)}</strong>
        </div>
      ))}
    </div>
  );
}
