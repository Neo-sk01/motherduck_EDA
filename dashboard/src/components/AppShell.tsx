import { ChevronDown, ChevronRight, CircleHelp, Download, RefreshCw } from "lucide-react";
import { useState, type ReactNode } from "react";
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

  const sourceGaps = report?.source_gaps.length ?? 0;
  const warning = loadResult?.status === "loaded" ? loadResult.warning : undefined;
  const isDegraded =
    sourceGaps > 0 ||
    Boolean(warning) ||
    validation === "failed";
  const [expanded, setExpanded] = useState(isDegraded);
  const showExpanded = expanded || isDegraded;
  const compactLabel = report
    ? `Loaded · ${report.date_range.start.slice(0, 7)} · Source: ${source}`
    : "Loading…";

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
      <div className={`status-strip ${showExpanded ? "is-expanded" : ""}`}>
        <button
          type="button"
          className="status-strip__toggle"
          aria-expanded={showExpanded}
          onClick={() => setExpanded((current) => !current)}
        >
          {showExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <span>{showExpanded ? "Hide status" : compactLabel}</span>
        </button>
        {showExpanded ? (
          <>
            <span>Source: {source}</span>
            <span className={validation === "failed" ? "warning" : ""}>Validation: {validation}</span>
            <span className={sourceGaps > 0 ? "warning" : ""}>Source gaps: {sourceGaps}</span>
            {warning ? <span className="warning">Fallback: {warning}</span> : null}
          </>
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
