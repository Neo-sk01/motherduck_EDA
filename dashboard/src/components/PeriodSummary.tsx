import { InfoPopover } from "./InfoPopover";
import { statusFor } from "../data/thresholds";
import type { PeriodSummary as PeriodSummaryData } from "../data/selectors";
import { formatInteger, formatPercent } from "../utils/format";

interface PeriodSummaryProps {
  summary: PeriodSummaryData;
  onAnomaliesClick: () => void;
}

export function PeriodSummary({ summary, onAnomaliesClick }: PeriodSummaryProps) {
  const reachStatus = statusFor("reached_an_agent", summary.reachedRate);
  const reachStatusLabel =
    reachStatus === "good" ? "Good" : reachStatus === "watch" ? "Watch" : reachStatus === "at-risk" ? "At risk" : null;

  return (
    <article className="period-summary">
      <div className="period-summary__headline">
        <p className="eyebrow">
          {summary.periodLabel}
          <InfoPopover infoId="period_total_calls" />
        </p>
        <strong>{formatInteger(summary.totalCalls)} calls handled</strong>
      </div>

      <div className="period-summary__cell">
        <p className="eyebrow">
          Reach rate
          <InfoPopover infoId="reach_rate" />
        </p>
        <strong>{formatPercent(summary.reachedRate)} reached an agent</strong>
        {reachStatusLabel ? (
          <span className={`metric-status-pill metric-status-pill--${reachStatus}`}>
            {reachStatusLabel}
          </span>
        ) : null}
      </div>

      <div className="period-summary__cell">
        <p className="eyebrow">
          Anomalies
          <InfoPopover infoId="anomaly_count" />
        </p>
        {summary.anomalyCount > 0 ? (
          <button
            type="button"
            className="period-summary__anomalies"
            onClick={onAnomaliesClick}
          >
            {formatInteger(summary.anomalyCount)} anomalies flagged
          </button>
        ) : (
          <span>No anomalies flagged.</span>
        )}
      </div>

      {summary.sourceGapCount > 0 ? (
        <div className="period-summary__cell period-summary__cell--warning">
          <p className="eyebrow">
            Coverage
            <InfoPopover infoId="source_gap" />
          </p>
          <strong>
            {formatInteger(summary.sourceGapCount)} source gap
            {summary.sourceGapCount === 1 ? "" : "s"}
          </strong>
        </div>
      ) : null}
    </article>
  );
}
