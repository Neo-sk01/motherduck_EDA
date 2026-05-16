import { useRef, useState } from "react";
import { AlertTriangle, ScrollText } from "lucide-react";
import { ChartFrame } from "../components/ChartFrame";
import { PeriodSummary } from "../components/PeriodSummary";
import { MetricCard } from "../components/MetricCard";
import { QueueCard } from "../components/QueueCard";
import { FunnelChart } from "../charts/FunnelChart";
import type { DashboardReport, QueueId, ViewKey } from "../data/reportTypes";
import { getLanguageFunnels, getPeriodSummary, getQueueSummaries, getTopAgent, getTopCaller } from "../data/selectors";
import { statusFor } from "../data/thresholds";
import { formatInteger, formatPercent, humanizeAnomalyKind } from "../utils/format";

interface OverviewViewProps {
  report: DashboardReport;
  onSelectQueue: (queueId: QueueId) => void;
  onNavigate: (view: ViewKey) => void;
}

export function OverviewView({ report, onSelectQueue, onNavigate }: OverviewViewProps) {
  const funnels = getLanguageFunnels(report);
  const summaries = getQueueSummaries(report);
  const periodSummary = getPeriodSummary(report);
  const anomalyStripRef = useRef<HTMLElement>(null);
  const topAgent = getTopAgent(report);
  const topCaller = getTopCaller(report);
  const [scrollableFunnels, setScrollableFunnels] = useState<Record<string, boolean>>({});

  return (
    <div className="view-stack">
      <section className="view-heading">
        <div>
          <h2>Period Health</h2>
          <p>Primary queues, overflow routing, and operational risks for the selected report.</p>
        </div>
        <div className="reference-row" aria-label="April reference values">
          <span>Queue 8020 {formatInteger(report.queues["8020"].total_calls)}</span>
          <span>{topAgent ? `${topAgent.agent_name} ${formatInteger(topAgent.total_calls)}` : "Top agent n/a"}</span>
          <span>
            {topCaller
              ? `Caller ${topCaller.caller_number_norm} ${formatInteger(topCaller.total_calls)}`
              : "Top caller n/a"}
          </span>
        </div>
      </section>

      <PeriodSummary
        summary={periodSummary}
        onAnomaliesClick={() =>
          anomalyStripRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
        }
      />

      <section className="funnel-grid">
        {funnels.map((item) => (
          <ChartFrame
            key={item.language}
            title={`${item.language} Funnel`}
            caption={`${item.language} routing match is ${formatPercent(item.funnel.routing_match)} for the period.`}
            filename={`${item.language.toLowerCase()}-funnel.png`}
            bodyClassName={scrollableFunnels[item.language] ? "chart-body--scrollable" : undefined}
            control={
              <label className="toggle toggle--switch">
                <input
                  type="checkbox"
                  checked={Boolean(scrollableFunnels[item.language])}
                  onChange={(event) =>
                    setScrollableFunnels((current) => ({
                      ...current,
                      [item.language]: event.target.checked,
                    }))
                  }
                />
                <span className="toggle-track" aria-hidden="true">
                  <span />
                </span>
                <ScrollText aria-hidden="true" size={14} />
                <span>Scroll</span>
              </label>
            }
          >
            <FunnelChart {...item} />
          </ChartFrame>
        ))}
      </section>

      <section className="metric-grid">
        {funnels.map((item) => (
          <MetricCard
            key={item.language}
            label={`${item.language}: reached an agent`}
            value={formatPercent(item.funnel.effective_answer_rate)}
            support={`${formatInteger(item.funnel.primary_calls - item.funnel.lost)} reached before final loss; ${formatInteger(item.funnel.lost)} lost`}
            metricId="reached_an_agent"
            status={statusFor("reached_an_agent", item.funnel.effective_answer_rate)}
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

      <section className="anomaly-strip" aria-label="Anomalies" ref={anomalyStripRef}>
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
            <strong>{humanizeAnomalyKind(anomaly.kind)}</strong>
            <p>{anomaly.description}</p>
          </button>
        ))}
      </section>
    </div>
  );
}
