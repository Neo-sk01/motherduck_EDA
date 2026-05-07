interface MetricCardProps {
  label: string;
  value: string;
  support?: string;
  tone?: "neutral" | "good" | "risk";
}

export function MetricCard({ label, value, support, tone = "neutral" }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <p className="eyebrow">{label}</p>
      <strong>{value}</strong>
      {support ? <span>{support}</span> : null}
    </article>
  );
}
