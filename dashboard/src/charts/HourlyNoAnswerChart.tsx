import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { QueueHourPoint } from "../data/reportTypes";
import { formatHour, formatPercent } from "../utils/format";

interface HourlyNoAnswerChartProps {
  data: QueueHourPoint[];
  color: string;
}

export function HourlyNoAnswerChart({ data, color }: HourlyNoAnswerChartProps) {
  return (
    <ResponsiveContainer width="100%" height={230}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid stroke="#E6E2DA" vertical={false} />
        <XAxis dataKey="hour" tickFormatter={formatHour} minTickGap={14} />
        <YAxis yAxisId="calls" allowDecimals={false} />
        <YAxis yAxisId="rate" orientation="right" tickFormatter={(value) => formatPercent(Number(value), 0)} />
        <Tooltip
          labelFormatter={(value) => formatHour(Number(value))}
          formatter={(value, name) =>
            name === "no_answer_rate" ? [formatPercent(Number(value)), "No-answer"] : [value, "Calls"]
          }
        />
        <Bar yAxisId="calls" dataKey="calls" fill={color} radius={[4, 4, 0, 0]} />
        <Line
          yAxisId="rate"
          dataKey="no_answer_rate"
          stroke="#A32D2D"
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
