import { ChartFrame } from "../components/ChartFrame";
import { DataTable, type DataColumn } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import { DailyVolumeChart } from "../charts/DailyVolumeChart";
import { DowChart } from "../charts/DowChart";
import { HourlyNoAnswerChart } from "../charts/HourlyNoAnswerChart";
import { ReleaseReasonsChart } from "../charts/ReleaseReasonsChart";
import type { DashboardReport, QueueAgent, QueueCaller, QueueId } from "../data/reportTypes";
import { QUEUE_META, QUEUE_ORDER } from "../data/reportTypes";
import { statusFor } from "../data/thresholds";
import {
  formatDecimal,
  formatDuration,
  formatHour,
  formatInteger,
  formatPercent,
  formatPhone,
} from "../utils/format";

interface PerQueueViewProps {
  report: DashboardReport;
  selectedQueueId: QueueId;
  onSelectQueue: (queueId: QueueId) => void;
}

export function PerQueueView({ report, selectedQueueId, onSelectQueue }: PerQueueViewProps) {
  const meta = QUEUE_META[selectedQueueId];
  const metrics = report.queues[selectedQueueId];
  const busiestHour =
    [...metrics.hourly_volume].sort((a, b) => b.calls - a.calls || a.hour - b.hour)[0]?.hour ?? null;
  const topAgent = metrics.agent_leaderboard[0];
  const topCaller = metrics.top_callers[0];
  const agentColumns: Array<DataColumn<QueueAgent & Record<string, unknown>>> = [
    { key: "agent_name", header: "Agent", value: (row) => row.agent_name },
    { key: "calls", header: "Calls", align: "right", value: (row) => row.calls },
    {
      key: "pct_of_answered",
      header: "% Answered",
      align: "right",
      value: (row) => row.pct_of_answered,
      render: (row) => formatPercent(row.pct_of_answered),
    },
    {
      key: "median_sec",
      header: "Median",
      align: "right",
      value: (row) => row.median_sec ?? 0,
      render: (row) => formatDuration(row.median_sec),
    },
  ];
  const callerColumns: Array<DataColumn<QueueCaller & Record<string, unknown>>> = [
    { key: "caller_number_norm", header: "Caller", value: (row) => row.caller_number_norm },
    { key: "calls", header: "Calls", align: "right", value: (row) => row.calls },
  ];

  return (
    <div className="view-stack">
      <section className="view-heading">
        <div>
          <h2>{meta.name}</h2>
          <p>{meta.id} · {meta.language} · {meta.role}</p>
        </div>
        <div className="segmented-control" aria-label="Select queue">
          {QUEUE_ORDER.map((queueId) => (
            <button
              key={queueId}
              type="button"
              className={queueId === selectedQueueId ? "is-active" : ""}
              onClick={() => onSelectQueue(queueId)}
            >
              {queueId}
            </button>
          ))}
        </div>
      </section>

      <section className="metric-grid metric-grid--six">
        <MetricCard label="Total calls" value={formatInteger(metrics.total_calls)} infoId="total_calls" />
        <MetricCard
          label="Avg per active day"
          value={formatDecimal(metrics.avg_calls_per_active_day)}
          infoId="avg_per_active_day"
        />
        <MetricCard
          label="Busiest day"
          value={metrics.busiest_day ? formatInteger(metrics.busiest_day.calls) : "0"}
          support={metrics.busiest_day?.date}
          infoId="busiest_day"
        />
        <MetricCard
          label="Missed-call rate"
          value={formatPercent(metrics.no_agent_rate)}
          infoId="missed_call_rate"
          status={statusFor("missed_call_rate", metrics.no_agent_rate)}
        />
        <MetricCard
          label="Peak hour"
          value={formatHour(busiestHour)}
          support={topAgent ? `Top agent ${topAgent.agent_name}` : "No handled calls"}
          infoId="peak_hour"
        />
        <MetricCard
          label="Top caller"
          value={topCaller ? formatPhone(topCaller.caller_number_norm) : "n/a"}
          support={topCaller ? `${formatInteger(topCaller.calls)} calls` : undefined}
          infoId="top_caller"
        />
      </section>

      <section className="chart-grid">
        <ChartFrame
          title="Daily Volume"
          caption="Busiest and quietest days are highlighted against the queue baseline."
          filename={`${selectedQueueId}-daily-volume.png`}
        >
          <DailyVolumeChart
            data={metrics.daily_volume}
            color={meta.color}
            busiest={metrics.busiest_day}
            quietest={metrics.quietest_day}
          />
        </ChartFrame>
        <ChartFrame
          title="Hourly Calls And No-Answer"
          caption="The red line reveals hours where no-answer pressure outpaces volume."
          filename={`${selectedQueueId}-hourly-no-answer.png`}
        >
          <HourlyNoAnswerChart data={metrics.hourly_volume} color={meta.color} />
        </ChartFrame>
        <ChartFrame
          title="Day Of Week"
          caption="Weekday distribution shows whether demand concentrates into a narrow cadence."
          filename={`${selectedQueueId}-dow.png`}
        >
          <DowChart data={metrics.dow_volume} color={meta.color} />
        </ChartFrame>
        <ChartFrame
          title="Queue Release Reasons"
          caption="Release reasons expose queue-side endings that deserve operational review."
          filename={`${selectedQueueId}-queue-release-reasons.png`}
        >
          <ReleaseReasonsChart data={metrics.release_reasons.queue} color={meta.color} />
        </ChartFrame>
      </section>

      <section className="chart-grid chart-grid--wide">
        <ChartFrame
          title="Agent Release Reasons"
          caption="Agent release reasons show how answered calls exit the agent leg."
          filename={`${selectedQueueId}-agent-release-reasons.png`}
        >
          <ReleaseReasonsChart data={metrics.release_reasons.agent} color={meta.color} />
        </ChartFrame>
        <DataTable
          title="Agent Leaderboard"
          rows={metrics.agent_leaderboard.slice(0, 10) as Array<QueueAgent & Record<string, unknown>>}
          columns={agentColumns}
          filename={`${selectedQueueId}-agent-leaderboard.csv`}
        />
        <DataTable
          title="Top Callers"
          rows={metrics.top_callers as Array<QueueCaller & Record<string, unknown>>}
          columns={callerColumns}
          filename={`${selectedQueueId}-top-callers.csv`}
        />
      </section>
    </div>
  );
}
