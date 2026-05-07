import { ChartFrame } from "../components/ChartFrame";
import { MetricCard } from "../components/MetricCard";
import { FunnelChart } from "../charts/FunnelChart";
import type { DashboardReport } from "../data/reportTypes";
import { getLanguageFunnels } from "../data/selectors";
import { formatInteger, formatPercent } from "../utils/format";

interface FunnelDetailViewProps {
  report: DashboardReport;
}

export function FunnelDetailView({ report }: FunnelDetailViewProps) {
  const funnels = getLanguageFunnels(report);

  return (
    <div className="view-stack">
      <section className="view-heading">
        <div>
          <h2>Funnel Detail</h2>
          <p>Primary-to-overflow routing, final loss, and unaccounted transfer gaps.</p>
        </div>
      </section>
      {funnels.map((item) => (
        <section className="language-detail" key={item.language}>
          <ChartFrame
            title={`${item.language} Routing Detail`}
            caption={`${item.language} shows ${formatPercent(item.funnel.routing_match)} routing match and ${formatPercent(item.funnel.effective_answer_rate)} effective answer rate.`}
            filename={`${item.language.toLowerCase()}-routing-detail.png`}
          >
            <FunnelChart {...item} />
          </ChartFrame>
          <div className="metric-grid metric-grid--six">
            <MetricCard label="Primary Calls" value={formatInteger(item.funnel.primary_calls)} />
            <MetricCard label="Primary Answered" value={formatInteger(item.funnel.primary_answered)} tone="good" />
            <MetricCard label="Primary Failed" value={formatInteger(item.funnel.primary_failed)} tone="risk" />
            <MetricCard label="Overflow Received" value={formatInteger(item.funnel.overflow_received)} />
            <MetricCard label="Overflow Answered" value={formatInteger(item.funnel.overflow_answered)} tone="good" />
            <MetricCard label="Lost" value={formatInteger(item.funnel.lost)} tone="risk" />
            <MetricCard label="Unaccounted" value={formatInteger(item.funnel.unaccounted)} />
            <MetricCard label="Routing Match" value={formatPercent(item.funnel.routing_match)} />
            <MetricCard label="Effective Answer" value={formatPercent(item.funnel.effective_answer_rate)} />
          </div>
        </section>
      ))}
    </div>
  );
}
