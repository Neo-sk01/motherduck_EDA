import { useState } from "react";
import { ChartFrame } from "../components/ChartFrame";
import { DataTable, type DataColumn } from "../components/DataTable";
import { SameDayVolumeOverlay, SameHourNoAnswerOverlay } from "../charts/OverlayCharts";
import type { ConsolidatedAgent, ConsolidatedCaller, DashboardReport } from "../data/reportTypes";
import { QUEUE_ORDER } from "../data/reportTypes";
import { getAgentRows, getCallerRows, getTopCaller, queueColumnValue } from "../data/selectors";
import { formatInteger, formatPhone } from "../utils/format";

interface CrossQueueViewProps {
  report: DashboardReport;
}

export function CrossQueueView({ report }: CrossQueueViewProps) {
  const [multiQueueOnly, setMultiQueueOnly] = useState(false);
  const [volumeMode, setVolumeMode] = useState<"raw" | "normalized">("raw");
  const agentRows = getAgentRows(report);
  const callerRows = getCallerRows(report, { multiQueueOnly });
  const topAgent = agentRows[0];
  const topCaller = getTopCaller(report);
  const agentColumns: Array<DataColumn<ConsolidatedAgent & Record<string, unknown>>> = [
    { key: "agent_name", header: "Agent", value: (row) => row.agent_name },
    ...QUEUE_ORDER.map((queueId) => ({
      key: queueId,
      header: queueId,
      align: "right" as const,
      value: (row: ConsolidatedAgent) => queueColumnValue(row, queueId),
      render: (row: ConsolidatedAgent) => formatInteger(queueColumnValue(row, queueId)),
    })),
    {
      key: "total_calls",
      header: "Total",
      align: "right",
      value: (row) => row.total_calls,
      render: (row) => formatInteger(row.total_calls),
    },
  ];
  const callerColumns: Array<DataColumn<ConsolidatedCaller & Record<string, unknown>>> = [
    { key: "caller_number_norm", header: "Caller", value: (row) => row.caller_number_norm },
    ...QUEUE_ORDER.map((queueId) => ({
      key: queueId,
      header: queueId,
      align: "right" as const,
      value: (row: ConsolidatedCaller) => queueColumnValue(row, queueId),
      render: (row: ConsolidatedCaller) => formatInteger(queueColumnValue(row, queueId)),
    })),
    {
      key: "total_calls",
      header: "Total",
      align: "right",
      value: (row) => row.total_calls,
      render: (row) => formatInteger(row.total_calls),
    },
  ];

  return (
    <div className="view-stack">
      <section className="view-heading">
        <div>
          <h2>Cross Queue Analytics</h2>
          <p>Consolidated agents, callers, no-answer timing, and same-day volume.</p>
        </div>
        <div className="reference-row" aria-label="Period references">
          <span className="reference-chip">
            <em className="eyebrow">Top agent</em>
            <strong>{topAgent?.agent_name ?? "n/a"}</strong>
            {topAgent ? <small>{formatInteger(topAgent.total_calls)} calls</small> : null}
          </span>
          <span className="reference-chip">
            <em className="eyebrow">Top caller</em>
            <strong>{topCaller ? formatPhone(topCaller.caller_number_norm) : "n/a"}</strong>
            {topCaller ? <small>{formatInteger(topCaller.total_calls)} calls</small> : null}
          </span>
        </div>
      </section>

      <section className="chart-grid">
        <DataTable
          title="Consolidated Agent Leaderboard"
          rows={agentRows as Array<ConsolidatedAgent & Record<string, unknown>>}
          columns={agentColumns}
          filename="crossqueue-agents.csv"
        />
        <DataTable
          title="Cross-Queue Caller Leaderboard"
          description="Toggle to isolate callers appearing on at least two queues."
          rows={callerRows as Array<ConsolidatedCaller & Record<string, unknown>>}
          columns={callerColumns}
          filename="crossqueue-callers.csv"
          headerAction={
            <label className="toggle">
              <input
                type="checkbox"
                checked={multiQueueOnly}
                onChange={(event) => setMultiQueueOnly(event.target.checked)}
              />
              2+ queues
            </label>
          }
        />
      </section>

      <section className="chart-grid">
        <ChartFrame
          title="Same-Hour No-Answer Overlay"
          caption="No-answer rates plotted together show whether misses cluster by hour."
          filename="same-hour-no-answer.png"
        >
          <SameHourNoAnswerOverlay report={report} />
        </ChartFrame>
        <ChartFrame
          title="Same-Day Volume Overlay"
          caption="Raw and normalized views separate absolute load from matching daily shape."
          filename="same-day-volume.png"
        >
          <div className="segmented-control segmented-control--small">
            <button
              type="button"
              className={volumeMode === "raw" ? "is-active" : ""}
              onClick={() => setVolumeMode("raw")}
            >
              Raw
            </button>
            <button
              type="button"
              className={volumeMode === "normalized" ? "is-active" : ""}
              onClick={() => setVolumeMode("normalized")}
            >
              Normalized
            </button>
          </div>
          <SameDayVolumeOverlay report={report} volumeMode={volumeMode} />
        </ChartFrame>
      </section>
    </div>
  );
}
