import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  it("renders label, value, and support", () => {
    render(<MetricCard label="Reached an agent" value="92.1%" support="1,048 of 1,247" />);
    expect(screen.getByText("Reached an agent")).toBeInTheDocument();
    expect(screen.getByText("92.1%")).toBeInTheDocument();
    expect(screen.getByText("1,048 of 1,247")).toBeInTheDocument();
  });

  it("shows a Good pill when status is good", () => {
    render(<MetricCard label="Reached an agent" value="92%" status="good" />);
    expect(screen.getByText("Good")).toBeInTheDocument();
  });

  it("shows a Watch pill when status is watch", () => {
    render(<MetricCard label="Reached an agent" value="84%" status="watch" />);
    expect(screen.getByText("Watch")).toBeInTheDocument();
  });

  it("shows an At risk pill when status is at-risk", () => {
    render(<MetricCard label="Reached an agent" value="70%" status="at-risk" />);
    expect(screen.getByText("At risk")).toBeInTheDocument();
  });

  it("renders an info trigger when infoId resolves in the metric info map", () => {
    render(<MetricCard label="Reached an agent" value="92%" infoId="reached_an_agent" />);
    expect(screen.getByRole("button", { name: /About Reached an agent/i })).toBeInTheDocument();
  });

  it("does not render an info trigger for unknown info ids", () => {
    render(<MetricCard label="Foo" value="1" infoId="unknown_metric" />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
