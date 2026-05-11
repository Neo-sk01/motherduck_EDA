import { describe, expect, it, vi } from "vitest";
import fixture from "../fixtures/april-2026-metrics.json";
import { loadReport, ReportValidationError, validateReport } from "./reportLoader";

describe("reportLoader", () => {
  it("validates the April fixture", () => {
    const report = validateReport(fixture);
    expect(report.queues["8020"].total_calls).toBe(1181);
    expect(report.crossqueue.funnels.English.routing_match).toBeCloseTo(0.983, 3);
  });

  it("rejects missing funnel data", () => {
    const invalid = structuredClone(fixture) as Record<string, unknown>;
    invalid.crossqueue = { agents: [], callers: [] };
    expect(() => validateReport(invalid)).toThrow(ReportValidationError);
  });

  it("loads a remote report when fetch succeeds", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => fixture,
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadReport({ path: "/metrics.json" });

    expect(result.status).toBe("loaded");
    expect(result.status === "loaded" && result.source).toBe("remote");
    expect(fetchMock).toHaveBeenCalledWith("/metrics.json", { cache: "no-store" });
    vi.unstubAllGlobals();
  });

  it("falls back to the fixture when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 404 })));

    const result = await loadReport({ path: "/missing.json" });

    expect(result.status).toBe("loaded");
    expect(result.status === "loaded" && result.source).toBe("fixture");
    expect(result.status === "loaded" && result.report.queues["8030"].total_calls).toBe(343);
    vi.unstubAllGlobals();
  });

  it("returns an error without fallback", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 500 })));

    const result = await loadReport({ path: "/broken.json", useFixtureFallback: false });

    expect(result).toMatchObject({
      status: "error",
      path: "/broken.json",
    });
    vi.unstubAllGlobals();
  });
});
