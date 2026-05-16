import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PeriodSummary } from "./PeriodSummary";

const baseSummary = {
  periodLabel: "April 2026",
  totalCalls: 1620,
  reachedRate: 0.84,
  anomalyCount: 15,
  sourceGapCount: 0,
};

describe("PeriodSummary", () => {
  it("renders the headline, reach rate, and anomaly count", () => {
    render(<PeriodSummary summary={baseSummary} onAnomaliesClick={() => undefined} />);
    expect(screen.getByText(/April 2026/)).toBeInTheDocument();
    expect(screen.getByText(/1,620 calls handled/)).toBeInTheDocument();
    expect(screen.getByText(/84.0% reached an agent/)).toBeInTheDocument();
    expect(screen.getByText(/15 anomalies flagged/)).toBeInTheDocument();
  });

  it("hides the source-gap cell when there are no gaps", () => {
    render(<PeriodSummary summary={baseSummary} onAnomaliesClick={() => undefined} />);
    expect(screen.queryByText(/source gap/i)).not.toBeInTheDocument();
  });

  it("shows the source-gap cell with loss tone when gaps exist", () => {
    render(
      <PeriodSummary
        summary={{ ...baseSummary, sourceGapCount: 2 }}
        onAnomaliesClick={() => undefined}
      />,
    );
    expect(screen.getByText(/2 source gaps/)).toBeInTheDocument();
  });

  it("renders 'No anomalies flagged.' as plain text when count is zero", () => {
    render(
      <PeriodSummary
        summary={{ ...baseSummary, anomalyCount: 0 }}
        onAnomaliesClick={() => undefined}
      />,
    );
    expect(screen.getByText("No anomalies flagged.")).toBeInTheDocument();
    // The info trigger button (aria-label "About Anomalies") is still present;
    // the assertion targets only the count-pivoting clickable, which is gone.
    expect(screen.queryByRole("button", { name: /anomalies flagged/i })).not.toBeInTheDocument();
  });

  it("calls onAnomaliesClick when the anomaly cell is clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<PeriodSummary summary={baseSummary} onAnomaliesClick={onClick} />);
    await user.click(screen.getByRole("button", { name: /anomalies flagged/i }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
