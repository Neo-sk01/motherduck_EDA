import { useEffect, useState } from "react";
import { AppShell } from "./components/AppShell";
import { EmptyState } from "./components/EmptyState";
import { DEFAULT_REPORT_PATH, loadReport } from "./data/reportLoader";
import type { DashboardReport, QueueId, ReportLoadResult, ViewKey } from "./data/reportTypes";
import { CrossQueueView } from "./views/CrossQueueView";
import { FunnelDetailView } from "./views/FunnelDetailView";
import { OverviewView } from "./views/OverviewView";
import { PerQueueView } from "./views/PerQueueView";

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>("overview");
  const [selectedQueueId, setSelectedQueueId] = useState<QueueId>("8020");
  const [reportPath, setReportPath] = useState(DEFAULT_REPORT_PATH);
  const [reloadToken, setReloadToken] = useState(0);
  const [loadResult, setLoadResult] = useState<ReportLoadResult | null>(null);

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

  return (
    <AppShell
      activeView={activeView}
      onViewChange={setActiveView}
      report={report}
      loadResult={loadResult}
      reportPath={reportPath}
      onReportPathChange={setReportPath}
      onReload={() => setReloadToken((current) => current + 1)}
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
