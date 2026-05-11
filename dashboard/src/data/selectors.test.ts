import { describe, expect, it } from "vitest";
import fixture from "../fixtures/april-2026-metrics.json";
import type { DashboardReport } from "./reportTypes";
import {
  getAgentRows,
  getCallerRows,
  getLanguageFunnels,
  getQueueSummaries,
  getTopAgent,
  getTopCaller,
} from "./selectors";

const report = fixture as DashboardReport;

describe("dashboard selectors", () => {
  it("returns queue summaries in queue order", () => {
    expect(getQueueSummaries(report).map((summary) => summary.meta.id)).toEqual([
      "8020",
      "8021",
      "8030",
      "8031",
    ]);
  });

  it("finds the April top agent and caller reference values", () => {
    expect(getTopAgent(report)).toMatchObject({
      agent_name: "Alicia Yameen",
      total_calls: 241,
    });
    expect(getTopCaller(report)).toMatchObject({
      caller_number_norm: "9052833500",
      total_calls: 63,
    });
  });

  it("keeps raw funnel values available", () => {
    const funnels = getLanguageFunnels(report);
    expect(funnels[0].language).toBe("English");
    expect(funnels[0].funnel.routing_match).toBeCloseTo(0.983, 3);
    expect(funnels[1].language).toBe("French");
    expect(funnels[1].funnel.effective_answer_rate).toBeCloseTo(0.879, 3);
  });

  it("filters callers that appear on at least two queues", () => {
    const rows = getCallerRows(report, { multiQueueOnly: true });
    expect(rows.every((row) => ["8020", "8021", "8030", "8031"].filter((id) => Number(row[id] ?? 0) > 0).length >= 2)).toBe(true);
  });

  it("sorts agent rows by total calls", () => {
    const rows = getAgentRows(report);
    expect(rows[0].total_calls).toBeGreaterThanOrEqual(rows[1].total_calls);
  });
});
