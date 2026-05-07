import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { QueueDowPoint } from "../data/reportTypes";

interface DowChartProps {
  data: QueueDowPoint[];
  color: string;
}

export function DowChart({ data, color }: DowChartProps) {
  return (
    <ResponsiveContainer width="100%" height={210}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid stroke="#E6E2DA" vertical={false} />
        <XAxis dataKey="dow" />
        <YAxis allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="calls" fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
