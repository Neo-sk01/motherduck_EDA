import { CircleHelp, Download, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import type { ReportOption } from "../data/reportManifest";
import type { DashboardReport, ReportLoadResult, ViewKey } from "../data/reportTypes";

export const VIEWS: Array<{ key: ViewKey; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "per-queue", label: "By Queue" },
  { key: "cross-queue", label: "Across Queues" },
  { key: "funnel-detail", label: "Routing Funnel" },
];

interface AppShellProps {
  activeView: ViewKey;
  onViewChange: (view: ViewKey) => void;
  report: DashboardReport | null;
  loadResult: ReportLoadResult | null;
  reportOptions: ReportOption[];
  selectedReportKey: string;
  onReportKeyChange: (key: string) => void;
  onReload: () => void;
  onExportReportCsv: () => void;
  onOpenTutorial: () => void;
  children: ReactNode;
}

export function AppShell({
  activeView,
  onViewChange,
  report,
  loadResult,
  reportOptions,
  selectedReportKey,
  onReportKeyChange,
  onReload,
  onExportReportCsv,
  onOpenTutorial,
  children,
}: AppShellProps) {
  const validation = report?.validation.status ?? "pending";
  const source = loadResult?.status === "loaded" ? loadResult.source : "remote";

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <img src="/neolore-logo.svg" alt="NeoLore Networks Inc." />
          <div>
            <h1>NeoLore Queue Analytics</h1>
            <p>
              {report
                ? `${report.date_range.start} through ${report.date_range.end}`
                : "Loading report"}
            </p>
          </div>
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
            <span>Report month</span>
            <select
              value={selectedReportKey}
              onChange={(event) => onReportKeyChange(event.target.value)}
            >
              {reportOptions.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label} · {formatSourceLabel(option.source)}
                </option>
              ))}
            </select>
          </label>
          <button className="text-button" type="button" onClick={onReload}>
            <RefreshCw aria-hidden="true" size={15} />
            Reload
          </button>
          <button className="text-button" type="button" onClick={onOpenTutorial}>
            <CircleHelp aria-hidden="true" size={15} />
            Open tutorial
          </button>
          <button
            className="text-button"
            type="button"
            onClick={onExportReportCsv}
            disabled={!report}
          >
            <Download aria-hidden="true" size={15} />
            Export CSV
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

function formatSourceLabel(source: string): string {
  if (source === "excel_reference_overlay") return "Excel";
  return source.toUpperCase();
}
