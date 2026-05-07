import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardReport, QueueId, SameDayVolumePoint } from "../data/reportTypes";
import { QUEUE_META, QUEUE_ORDER } from "../data/reportTypes";
import { normalizeSameDayVolume } from "../data/selectors";
import { formatDateLabel, formatHour, formatPercent } from "../utils/format";

interface OverlayProps {
  report: DashboardReport;
  volumeMode?: "raw" | "normalized";
}

export function SameHourNoAnswerOverlay({ report }: OverlayProps) {
  const data = Array.from({ length: 24 }, (_, hour) => {
    const row: Record<string, number> = { hour };
    for (const queueId of QUEUE_ORDER) row[queueId] = 0;
    for (const point of report.crossqueue.same_hour_no_answer.filter((item) => item.hour === hour)) {
      row[point.queue_id] = point.no_answer_rate;
    }
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 10, bottom: 0, left: -20 }}>
        <CartesianGrid stroke="#E6E2DA" vertical={false} />
        <XAxis dataKey="hour" tickFormatter={formatHour} />
        <YAxis tickFormatter={(value) => formatPercent(Number(value), 0)} />
        <Tooltip
          labelFormatter={(value) => formatHour(Number(value))}
          formatter={(value) => formatPercent(Number(value))}
        />
        {QUEUE_ORDER.map((queueId) => (
          <Line
            key={queueId}
            dataKey={queueId}
            stroke={QUEUE_META[queueId].color}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SameDayVolumeOverlay({ report, volumeMode = "raw" }: OverlayProps) {
  const source =
    volumeMode === "normalized"
      ? normalizeSameDayVolume(report.crossqueue.same_day_volume)
      : report.crossqueue.same_day_volume;
  const data = pivotDays(source);

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 10, bottom: 0, left: -20 }}>
        <CartesianGrid stroke="#E6E2DA" vertical={false} />
        <XAxis dataKey="date" tickFormatter={formatDateLabel} minTickGap={18} />
        <YAxis />
        <Tooltip
          labelFormatter={(value) => String(value)}
          formatter={(value) =>
            volumeMode === "normalized" ? formatPercent(Number(value), 0) : Number(value)
          }
        />
        {QUEUE_ORDER.map((queueId) => (
          <Line
            key={queueId}
            dataKey={queueId}
            stroke={QUEUE_META[queueId].color}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function pivotDays(points: SameDayVolumePoint[]): Array<Record<string, string | number>> {
  const byDate = new Map<string, Record<string, string | number>>();
  for (const point of points) {
    const row = byDate.get(point.date) ?? { date: point.date };
    row[point.queue_id] = point.calls;
    byDate.set(point.date, row);
  }
  return [...byDate.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
}
