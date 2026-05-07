import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ReasonCount } from "../data/reportTypes";

interface ReleaseReasonsChartProps {
  data: ReasonCount[];
  color: string;
}

export function ReleaseReasonsChart({ data, color }: ReleaseReasonsChartProps) {
  const rows = data.slice(0, 8);
  if (rows.length === 0) return <p className="muted">No release reasons present in this report.</p>;

  return (
    <ResponsiveContainer width="100%" height={Math.max(180, rows.length * 34)}>
      <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 16, bottom: 0, left: 96 }}>
        <CartesianGrid stroke="#E6E2DA" horizontal={false} />
        <XAxis type="number" allowDecimals={false} />
        <YAxis type="category" dataKey="reason" width={96} tick={{ fontSize: 11 }} />
        <Tooltip />
        <Bar dataKey="calls" fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
