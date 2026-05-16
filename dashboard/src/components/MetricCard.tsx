import { InfoPopover } from "./InfoPopover";
import { getMetricInfo } from "../data/metricInfo";
import type { MetricStatus } from "../data/thresholds";

interface MetricCardProps {
  label: string;
  value: string;
  support?: string;
  status?: MetricStatus;
  infoId?: string;
}

const STATUS_LABELS: Record<MetricStatus, string> = {
  good: "Good",
  watch: "Watch",
  "at-risk": "At risk",
};

export function MetricCard({ label, value, support, status, infoId }: MetricCardProps) {
  const hasInfo = Boolean(getMetricInfo(infoId));
  const statusClass = status ? ` metric-card--${status}` : "";

  return (
    <article className={`metric-card${statusClass}`}>
      <div className="metric-card__head">
        <p className="eyebrow">
          {label}
          {hasInfo && infoId ? <InfoPopover infoId={infoId} /> : null}
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
