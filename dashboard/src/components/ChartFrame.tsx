import { useRef, useState, type ReactNode } from "react";
import { downloadElementPng } from "../utils/exportPng";
import { ExportButton } from "./ExportButton";

interface ChartFrameProps {
  title: string;
  caption: string;
  filename: string;
  control?: ReactNode;
  bodyClassName?: string;
  children: ReactNode;
}

export function ChartFrame({ title, caption, filename, control, bodyClassName, children }: ChartFrameProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    if (!ref.current) return;
    setError(null);
    try {
      await downloadElementPng(ref.current, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "PNG export failed.");
    }
  }

  return (
    <section className="chart-frame" ref={ref}>
      <div className="frame-heading">
        <div>
          <h3>{title}</h3>
          <p>{caption}</p>
        </div>
        <div className="frame-actions">
          {control}
          <ExportButton label={`Export ${title} PNG`} onClick={handleExport} />
        </div>
      </div>
      <div className={["chart-body", bodyClassName].filter(Boolean).join(" ")}>{children}</div>
      {error ? <p className="inline-error">{error}</p> : null}
    </section>
  );
}
