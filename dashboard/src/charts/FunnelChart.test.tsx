import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FunnelChart } from "./FunnelChart";
import type { FunnelMetrics } from "../data/reportTypes";

const englishFunnel: FunnelMetrics = {
  primary_calls: 1181,
  primary_answered: 832,
  primary_failed: 349,
  overflow_received: 343,
  overflow_answered: 162,
  overflow_failed: 181,
  lost: 181,
  lost_rate: 181 / 1181,
  unaccounted: 6,
  routing_match: 0.983,
  effective_answer_rate: 0.847,
};

describe("FunnelChart", () => {
  it("renders the hero number with 'Calls in' eyebrow", () => {
    render(
      <FunnelChart
        language="English"
        funnel={englishFunnel}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    expect(screen.getByText("Calls in")).toBeInTheDocument();
    expect(screen.getByText("1,181")).toBeInTheDocument();
  });

  it("shows both rate pills with plain-English labels", () => {
    render(
      <FunnelChart
        language="English"
        funnel={englishFunnel}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    expect(screen.getByText(/Right-language routing 98.3%/)).toBeInTheDocument();
    expect(screen.getByText(/Reached an agent 84.7%/)).toBeInTheDocument();
  });

  it("renders a legend row for each outcome slice with its count", () => {
    render(
      <FunnelChart
        language="English"
        funnel={englishFunnel}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    const legend = screen.getByRole("list");
    expect(within(legend).getByText("Answered on primary")).toBeInTheDocument();
    expect(within(legend).getByText("832")).toBeInTheDocument();
    expect(within(legend).getByText("Answered on overflow")).toBeInTheDocument();
    expect(within(legend).getByText("162")).toBeInTheDocument();
    expect(within(legend).getByText("Never connected")).toBeInTheDocument();
    expect(within(legend).getByText("Untracked")).toBeInTheDocument();
    expect(within(legend).getByText("6")).toBeInTheDocument();
  });

  it("hides slices whose value is zero", () => {
    render(
      <FunnelChart
        language="English"
        funnel={{ ...englishFunnel, unaccounted: 0 }}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    const legend = screen.getByRole("list");
    expect(within(legend).queryByText("Untracked")).not.toBeInTheDocument();
  });
});
