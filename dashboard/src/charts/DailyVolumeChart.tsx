import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { QueueDayPoint } from "../data/reportTypes";
import { formatDateLabel } from "../utils/format";

interface DailyVolumeChartProps {
  data: QueueDayPoint[];
  color: string;
  busiest?: QueueDayPoint | null;
  quietest?: QueueDayPoint | null;
}

export function DailyVolumeChart({ data, color, busiest, quietest }: DailyVolumeChartProps) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid stroke="#E6E2DA" vertical={false} />
        <XAxis dataKey="date" tickFormatter={formatDateLabel} minTickGap={18} />
        <YAxis allowDecimals={false} />
        <Tooltip labelFormatter={(value) => String(value)} />
        <Bar dataKey="calls" radius={[4, 4, 0, 0]}>
          {data.map((point) => (
            <Cell
              key={point.date}
              fill={
                point.date === busiest?.date
                  ? "#A07A25"
                  : point.date === quietest?.date
                    ? "#B86B5F"
                    : color
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
