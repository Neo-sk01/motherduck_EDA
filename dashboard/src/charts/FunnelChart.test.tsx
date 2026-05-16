import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FunnelChart } from "./FunnelChart";
import type { FunnelMetrics } from "../data/reportTypes";

const englishFunnel: FunnelMetrics = {
  primary_calls: 1181,
  primary_answered: 800,
  primary_failed: 200,
  overflow_received: 181,
  overflow_answered: 150,
  overflow_failed: 31,
  lost: 25,
  lost_rate: 25 / 1181,
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

  it("renders the outcome strip with reached, never-connected, and hides untracked when zero", () => {
    render(
      <FunnelChart
        language="English"
        funnel={{ ...englishFunnel, unaccounted: 0 }}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    expect(screen.getByText(/Reached someone:/)).toBeInTheDocument();
    expect(screen.getByText(/Never connected:/)).toBeInTheDocument();
    expect(screen.queryByText(/Untracked:/)).not.toBeInTheDocument();
  });

  it("shows the untracked chip when unaccounted > 0", () => {
    render(
      <FunnelChart
        language="English"
        funnel={englishFunnel}
        primaryQueue="8020"
        overflowQueue="8030"
      />,
    );
    expect(screen.getByText(/Untracked: 6/)).toBeInTheDocument();
  });

  it("hides the overflow detail bar when overflow_received is zero", () => {
    render(
      <FunnelChart
        language="French"
        funnel={{ ...englishFunnel, overflow_received: 0, overflow_answered: 0 }}
        primaryQueue="8021"
        overflowQueue="8031"
      />,
    );
    expect(screen.queryByText(/Answered on overflow/)).not.toBeInTheDocument();
  });
});
