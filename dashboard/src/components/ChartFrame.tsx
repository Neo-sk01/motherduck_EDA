import { useRef, useState, type ReactNode } from "react";
import { downloadElementPng } from "../utils/exportPng";
import { ExportButton } from "./ExportButton";

interface ChartFrameProps {
  title: string;
  caption: string;
  filename: string;
  children: ReactNode;
}

export function ChartFrame({ title, caption, filename, children }: ChartFrameProps) {
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
        <ExportButton label={`Export ${title} PNG`} onClick={handleExport} />
      </div>
      <div className="chart-body">{children}</div>
      {error ? <p className="inline-error">{error}</p> : null}
    </section>
  );
}
