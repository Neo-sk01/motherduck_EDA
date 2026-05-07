import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import type { DashboardReport, ReportLoadResult, ViewKey } from "../data/reportTypes";

export const VIEWS: Array<{ key: ViewKey; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "per-queue", label: "Per Queue" },
  { key: "cross-queue", label: "Cross Queue" },
  { key: "funnel-detail", label: "Funnel Detail" },
];

interface AppShellProps {
  activeView: ViewKey;
  onViewChange: (view: ViewKey) => void;
  report: DashboardReport | null;
  loadResult: ReportLoadResult | null;
  reportPath: string;
  onReportPathChange: (path: string) => void;
  onReload: () => void;
  children: ReactNode;
}

export function AppShell({
  activeView,
  onViewChange,
  report,
  loadResult,
  reportPath,
  onReportPathChange,
  onReload,
  children,
}: AppShellProps) {
  const validation = report?.validation.status ?? "pending";
  const source = loadResult?.status === "loaded" ? loadResult.source : "remote";

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <h1>NeoLore Queue Analytics</h1>
          <p>
            {report
              ? `${report.date_range.start} through ${report.date_range.end}`
              : "Loading report"}
          </p>
        </div>
        <nav className="tabs" aria-label="Dashboard views">
          {VIEWS.map((view) => (
            <button
              key={view.key}
              type="button"
              className={activeView === view.key ? "is-active" : ""}
              onClick={() => onViewChange(view.key)}
            >
              {view.label}
            </button>
          ))}
        </nav>
        <div className="report-controls">
          <label>
            <span>Report path</span>
            <input
              value={reportPath}
              onChange={(event) => onReportPathChange(event.target.value)}
            />
          </label>
          <button className="text-button" type="button" onClick={onReload}>
            <RefreshCw aria-hidden="true" size={15} />
            Reload
          </button>
        </div>
      </header>
      <div className="status-strip">
        <span>Source: {source}</span>
        <span>Validation: {validation}</span>
        <span>Source gaps: {report?.source_gaps.length ?? 0}</span>
        {loadResult?.status === "loaded" && loadResult.warning ? (
          <span className="warning">Fallback: {loadResult.warning}</span>
        ) : null}
      </div>
      <main>{children}</main>
    </div>
  );
}
