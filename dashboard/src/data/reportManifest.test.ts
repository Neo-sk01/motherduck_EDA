import { describe, expect, it, vi } from "vitest";
import {
  DEFAULT_REPORT_OPTION,
  buildReportPath,
  loadReportManifest,
  sortReportOptions,
} from "./reportManifest";

describe("reportManifest", () => {
  it("builds report paths from month ranges", () => {
    expect(buildReportPath("2026-03-01", "2026-03-31")).toBe(
      "/data/reports/month_2026-03-01_2026-03-31/metrics.json",
    );
  });

  it("sorts report options with the newest month first", () => {
    expect(
      sortReportOptions([
        { key: "2026-01", label: "January 2026", start: "2026-01-01", end: "2026-01-31", path: "/jan.json", source: "api" },
        { key: "2026-03", label: "March 2026", start: "2026-03-01", end: "2026-03-31", path: "/mar.json", source: "api" },
      ]).map((option) => option.key),
    ).toEqual(["2026-03", "2026-01"]);
  });

  it("loads manifest options when available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          reports: [
            {
              key: "2026-02",
              label: "February 2026",
              start: "2026-02-01",
              end: "2026-02-28",
              path: "/data/reports/month_2026-02-01_2026-02-28/metrics.json",
              source: "api",
            },
          ],
        }),
      })),
    );

    const options = await loadReportManifest();

    expect(options).toHaveLength(1);
    expect(options[0].key).toBe("2026-02");
    vi.unstubAllGlobals();
  });

  it("falls back to the April report when the manifest is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 404 })));

    await expect(loadReportManifest()).resolves.toEqual([DEFAULT_REPORT_OPTION]);
    vi.unstubAllGlobals();
  });
});
