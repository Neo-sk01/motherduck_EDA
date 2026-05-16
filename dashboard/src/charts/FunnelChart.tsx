import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";
import { InfoPopover } from "../components/InfoPopover";
import type { FunnelMetrics, QueueId } from "../data/reportTypes";
import { QUEUE_META } from "../data/reportTypes";
import { formatInteger, formatPercent } from "../utils/format";

interface FunnelChartProps {
  language: "English" | "French";
  funnel: FunnelMetrics;
  primaryQueue: QueueId;
  overflowQueue: QueueId;
}

const LOSS_COLOR = "#8f2f2f";
const UNTRACKED_COLOR = "#8b7a28";

export function FunnelChart({ language, funnel, primaryQueue, overflowQueue }: FunnelChartProps) {
  const primaryColor = QUEUE_META[primaryQueue].color;
  const overflowColor = QUEUE_META[overflowQueue].color;

  const slices = [
    {
      key: "answered_primary",
      label: "Answered on primary",
      value: funnel.primary_answered,
      color: primaryColor,
    },
    {
      key: "answered_overflow",
      label: "Answered on overflow",
      value: funnel.overflow_answered,
      color: overflowColor,
    },
    {
      key: "never_connected",
      label: "Never connected",
      value: funnel.lost,
      color: LOSS_COLOR,
    },
    {
      key: "untracked",
      label: "Untracked",
      value: funnel.unaccounted,
      color: UNTRACKED_COLOR,
    },
  ].filter((slice) => slice.value > 0);

  return (
    <div className="funnel-chart" aria-label={`${language} routing funnel`}>
      <div className="funnel-hero">
        <p className="eyebrow">Calls in</p>
        <strong>{formatInteger(funnel.primary_calls)}</strong>
      </div>

      <div className="funnel-rates">
        <span>
          Right-language routing {formatPercent(funnel.routing_match)}
          <InfoPopover infoId="right_language_routing" />
        </span>
        <span>
          Reached an agent {formatPercent(funnel.effective_answer_rate)}
          <InfoPopover infoId="reached_an_agent" />
        </span>
      </div>

      <div className="funnel-pie-wrap">
        <div className="funnel-pie">
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={slices}
                dataKey="value"
                nameKey="label"
                outerRadius={80}
                innerRadius={0}
                strokeWidth={1}
                isAnimationActive={false}
              >
                {slices.map((slice) => (
                  <Cell key={slice.key} fill={slice.color} />
                ))}
              </Pie>
              <RechartsTooltip
                formatter={(value: number, name: string) => [formatInteger(value), name]}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <ul className="funnel-legend">
          {slices.map((slice) => (
            <li key={slice.key}>
              <span className="funnel-legend__swatch" style={{ backgroundColor: slice.color }} />
              <span className="funnel-legend__label">{slice.label}</span>
              <span className="funnel-legend__value">{formatInteger(slice.value)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
