import { Tooltip } from "./Tooltip";
import { getGlossaryEntry } from "../data/glossary";
import type { MetricStatus } from "../data/thresholds";

interface MetricCardProps {
  label: string;
  value: string;
  support?: string;
  status?: MetricStatus;
  metricId?: string;
}

const STATUS_LABELS: Record<MetricStatus, string> = {
  good: "Good",
  watch: "Watch",
  "at-risk": "At risk",
};

export function MetricCard({ label, value, support, status, metricId }: MetricCardProps) {
  const glossaryEntry = getGlossaryEntry(metricId);
  const toneClass = status ? `metric-card--${status}` : "metric-card--neutral";

  return (
    <article className={`metric-card ${toneClass}`}>
      <div className="metric-card__head">
        <p className="eyebrow">
          {label}
          {glossaryEntry && metricId ? (
            <Tooltip id={`${metricId}-tip`} label={label} content={glossaryEntry} />
          ) : null}
        </p>
        {status ? (
          <span className={`metric-status-pill metric-status-pill--${status}`}>
            {STATUS_LABELS[status]}
          </span>
        ) : null}
      </div>
      <strong>{value}</strong>
      {support ? <span>{support}</span> : null}
    </article>
  );
}
