import { AlertTriangle } from "lucide-react";
import { ChartFrame } from "../components/ChartFrame";
import { MetricCard } from "../components/MetricCard";
import { QueueCard } from "../components/QueueCard";
import { FunnelChart } from "../charts/FunnelChart";
import type { DashboardReport, QueueId, ViewKey } from "../data/reportTypes";
import { getLanguageFunnels, getQueueSummaries } from "../data/selectors";
import { formatInteger, formatPercent, titleCase } from "../utils/format";

interface OverviewViewProps {
  report: DashboardReport;
  onSelectQueue: (queueId: QueueId) => void;
  onNavigate: (view: ViewKey) => void;
}

export function OverviewView({ report, onSelectQueue, onNavigate }: OverviewViewProps) {
  const funnels = getLanguageFunnels(report);
  const summaries = getQueueSummaries(report);

  return (
    <div className="view-stack">
      <section className="view-heading">
        <div>
          <h2>Period Health</h2>
          <p>Primary queues, overflow routing, and operational risks for the selected report.</p>
        </div>
        <div className="reference-row" aria-label="April reference values">
          <span>Gabriel Hubert 299</span>
          <span>Caller 9052833500 63</span>
        </div>
      </section>

      <section className="funnel-grid">
        {funnels.map((item) => (
          <ChartFrame
            key={item.language}
            title={`${item.language} Funnel`}
            caption={`${item.language} routing match is ${formatPercent(item.funnel.routing_match)} for the period.`}
            filename={`${item.language.toLowerCase()}-funnel.png`}
          >
            <FunnelChart {...item} />
          </ChartFrame>
        ))}
      </section>

      <section className="metric-grid">
        {funnels.map((item) => (
          <MetricCard
            key={item.language}
            label={`${item.language} Effective Answer`}
            value={formatPercent(item.funnel.effective_answer_rate)}
            support={`${formatInteger(item.funnel.primary_calls - item.funnel.lost)} reached before final loss; ${formatInteger(item.funnel.lost)} lost`}
            tone={item.funnel.effective_answer_rate >= 0.85 ? "good" : "risk"}
          />
        ))}
      </section>

      <section className="queue-grid" aria-label="Queue cards">
        {summaries.map((summary) => (
          <QueueCard
            key={summary.meta.id}
            summary={summary}
            onOpen={() => {
              onSelectQueue(summary.meta.id);
              onNavigate("per-queue");
            }}
          />
        ))}
      </section>

      <section className="anomaly-strip" aria-label="Anomalies">
        <div className="section-kicker">
          <AlertTriangle aria-hidden="true" size={16} />
          <h3>Anomaly Strip</h3>
        </div>
        {report.anomalies.slice(0, 8).map((anomaly, index) => (
          <button
            type="button"
            key={`${anomaly.kind}-${index}`}
            className={`anomaly-card anomaly-card--${anomaly.severity}`}
            onClick={() => {
              if (anomaly.target?.queue_id) onSelectQueue(anomaly.target.queue_id);
              if (anomaly.target?.view === "cross-queue") onNavigate("cross-queue");
              else if (anomaly.target?.view === "per-queue") onNavigate("per-queue");
            }}
          >
            <span>{anomaly.severity}</span>
            <strong>{titleCase(anomaly.kind)}</strong>
            <p>{anomaly.description}</p>
          </button>
        ))}
      </section>
    </div>
  );
}
