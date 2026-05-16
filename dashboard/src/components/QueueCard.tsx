import type { QueueSummary } from "../data/selectors";
import { formatHour, formatInteger, formatPercent } from "../utils/format";

interface QueueCardProps {
  summary: QueueSummary;
  onOpen: () => void;
}

export function QueueCard({ summary, onOpen }: QueueCardProps) {
  const points = summary.metrics.daily_volume;
  const max = Math.max(...points.map((point) => point.calls), 1);

  return (
    <button className="queue-card" type="button" onClick={onOpen}>
      <span className="queue-chip" style={{ "--queue-color": summary.meta.color } as React.CSSProperties}>
        {summary.meta.language === "English" ? "EN" : "FR"}
        <em>{summary.meta.role === "primary" ? "Pri" : "Ovr"}</em>
      </span>
      <div>
        <h3>{summary.meta.name}</h3>
        <p>
          {summary.meta.id} · {summary.meta.language} · {summary.meta.role}
        </p>
      </div>
      <strong>{formatInteger(summary.metrics.total_calls)}</strong>
      <dl>
        <div>
          <dt>Missed-call rate</dt>
          <dd>{formatPercent(summary.metrics.no_agent_rate)}</dd>
        </div>
        <div>
          <dt>Peak hour</dt>
          <dd>{formatHour(summary.busiestHour)}</dd>
        </div>
        <div>
          <dt>Top agent</dt>
          <dd>{summary.topAgent}</dd>
        </div>
      </dl>
      <div className="sparkline" aria-hidden="true">
        {points.slice(0, 30).map((point) => (
          <span
            key={point.date}
            style={{
              height: `${Math.max(10, (point.calls / max) * 100)}%`,
              backgroundColor: summary.meta.color,
            }}
          />
        ))}
      </div>
    </button>
  );
}
