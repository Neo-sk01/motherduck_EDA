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
    { label: "Calls in", value: funnel.primary_calls, color: QUEUE_META[primaryQueue].color },
    { label: "Answered on primary", value: funnel.primary_answered, color: "#2B7A4B" },
    { label: "Missed on primary", value: funnel.primary_failed, color: "#A32D2D" },
    { label: "Sent to overflow", value: funnel.overflow_received, color: QUEUE_META[overflowQueue].color },
    { label: "Answered on overflow", value: funnel.overflow_answered, color: "#2B7A4B" },
    { label: "Never connected", value: funnel.lost, color: "#A32D2D" },
    { label: "Untracked", value: funnel.unaccounted, color: "#7B6B3A" },
  ];

  return (
    <div className="funnel-chart" aria-label={`${language} routing funnel`}>
      <div className="funnel-rates">
        <span>Right-language routing {formatPercent(funnel.routing_match)}</span>
        <span>Reached an agent {formatPercent(funnel.effective_answer_rate)}</span>
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
