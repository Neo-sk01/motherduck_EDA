import { useEffect, useState } from "react";
import { AppShell } from "./components/AppShell";
import { EmptyState } from "./components/EmptyState";
import { DEFAULT_REPORT_PATH, loadReport } from "./data/reportLoader";
import {
  DEFAULT_REPORT_OPTION,
  loadReportManifest,
  type ReportOption,
} from "./data/reportManifest";
import type { DashboardReport, QueueId, ReportLoadResult, ViewKey } from "./data/reportTypes";
import { downloadFullReportCsv } from "./utils/reportExport";
import { CrossQueueView } from "./views/CrossQueueView";
import { FunnelDetailView } from "./views/FunnelDetailView";
import { OverviewView } from "./views/OverviewView";
import { PerQueueView } from "./views/PerQueueView";

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>("overview");
  const [selectedQueueId, setSelectedQueueId] = useState<QueueId>("8020");
  const [reportPath, setReportPath] = useState(DEFAULT_REPORT_PATH);
  const [reportOptions, setReportOptions] = useState<ReportOption[]>([DEFAULT_REPORT_OPTION]);
  const [selectedReportKey, setSelectedReportKey] = useState(DEFAULT_REPORT_OPTION.key);
  const [reloadToken, setReloadToken] = useState(0);
  const [loadResult, setLoadResult] = useState<ReportLoadResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadReportManifest().then((options) => {
      if (cancelled) return;
      setReportOptions(options);
      const selected = options.find((option) => option.path === reportPath) ?? options[0];
      setSelectedReportKey(selected.key);
      setReportPath(selected.path);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadResult(null);
    loadReport({ path: reportPath }).then((result) => {
      if (!cancelled) setLoadResult(result);
    });
    return () => {
      cancelled = true;
    };
  }, [reloadToken, reportPath]);

  const report = loadResult?.status === "loaded" ? loadResult.report : null;
  const handleReportKeyChange = (key: string) => {
    const option = reportOptions.find((candidate) => candidate.key === key);
    if (!option) return;
    setSelectedReportKey(option.key);
    setReportPath(option.path);
  };

  return (
    <AppShell
      activeView={activeView}
      onViewChange={setActiveView}
      report={report}
      loadResult={loadResult}
      reportOptions={reportOptions}
      selectedReportKey={selectedReportKey}
      onReportKeyChange={handleReportKeyChange}
      onReload={() => setReloadToken((current) => current + 1)}
      onExportReportCsv={() => {
        if (report) downloadFullReportCsv(report);
      }}
    >
      {renderContent({
        activeView,
        report,
        loadResult,
        selectedQueueId,
        setSelectedQueueId,
        setActiveView,
        reportPath,
      })}
    </AppShell>
  );
}

function renderContent({
  activeView,
  report,
  loadResult,
  selectedQueueId,
  setSelectedQueueId,
  setActiveView,
  reportPath,
}: {
  activeView: ViewKey;
  report: DashboardReport | null;
  loadResult: ReportLoadResult | null;
  selectedQueueId: QueueId;
  setSelectedQueueId: (queueId: QueueId) => void;
  setActiveView: (view: ViewKey) => void;
  reportPath: string;
}) {
  if (loadResult?.status === "error") {
    return (
      <EmptyState
        title="Report could not be loaded"
        path={loadResult.path}
        message={loadResult.error}
      />
    );
  }
  if (!report) {
    return <section className="loading-state">Loading dashboard report...</section>;
  }

  if (activeView === "overview") {
    return (
      <OverviewView
        report={report}
        onSelectQueue={setSelectedQueueId}
        onNavigate={setActiveView}
      />
    );
  }
  if (activeView === "per-queue") {
    return (
      <PerQueueView
        report={report}
        selectedQueueId={selectedQueueId}
        onSelectQueue={setSelectedQueueId}
      />
    );
  }
  if (activeView === "cross-queue") {
    return <CrossQueueView report={report} />;
  }
  if (activeView === "funnel-detail") {
    return <FunnelDetailView report={report} />;
  }

  return (
    <EmptyState
      title="Unknown dashboard view"
      path={reportPath}
      message="Choose one of the available dashboard tabs."
    />
  );
}
