import { ChartFrame } from "../components/ChartFrame";
import { MetricCard } from "../components/MetricCard";
import { FunnelChart } from "../charts/FunnelChart";
import type { DashboardReport } from "../data/reportTypes";
import { getLanguageFunnels } from "../data/selectors";
import { statusFor } from "../data/thresholds";
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
          <h2>Routing Funnel</h2>
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
            <MetricCard label="Calls in" value={formatInteger(item.funnel.primary_calls)} infoId="calls_in" />
            <MetricCard
              label="Answered on primary"
              value={formatInteger(item.funnel.primary_answered)}
              status="good"
              infoId="answered_on_primary"
            />
            <MetricCard
              label="Missed on primary"
              value={formatInteger(item.funnel.primary_failed)}
              status="at-risk"
              infoId="missed_on_primary"
            />
            <MetricCard
              label="Sent to overflow"
              value={formatInteger(item.funnel.overflow_received)}
              infoId="sent_to_overflow"
            />
            <MetricCard
              label="Answered on overflow"
              value={formatInteger(item.funnel.overflow_answered)}
              status="good"
              infoId="answered_on_overflow"
            />
            <MetricCard
              label="Never connected"
              value={formatInteger(item.funnel.lost)}
              status="at-risk"
              infoId="never_connected"
            />
            <MetricCard
              label="Untracked"
              value={formatInteger(item.funnel.unaccounted)}
              infoId="untracked"
            />
            <MetricCard
              label="Right-language routing"
              value={formatPercent(item.funnel.routing_match)}
              infoId="right_language_routing"
              status={statusFor("right_language_routing", item.funnel.routing_match)}
            />
            <MetricCard
              label="Reached an agent"
              value={formatPercent(item.funnel.effective_answer_rate)}
              infoId="reached_an_agent"
              status={statusFor("reached_an_agent", item.funnel.effective_answer_rate)}
            />
          </div>
        </section>
      ))}
    </div>
  );
}
