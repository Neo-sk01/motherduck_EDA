import { describe, expect, it, vi } from "vitest";
import {
  DEFAULT_REPORT_OPTION,
  buildReportPath,
  loadReportManifest,
  resolveReportsBaseUrl,
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

describe("resolveReportsBaseUrl", () => {
  it("uses VITE_REPORTS_BASE_URL when set, stripping trailing slash", () => {
    expect(resolveReportsBaseUrl({ VITE_REPORTS_BASE_URL: "https://x.blob.core.windows.net/reports/" }))
      .toBe("https://x.blob.core.windows.net/reports");
  });

  it("falls back to /data/reports when env var is unset", () => {
    expect(resolveReportsBaseUrl({})).toBe("/data/reports");
  });
});

describe("manifest entries with relative paths", () => {
  it("prepends the base URL to relative paths from manifest", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          reports: [{
            key: "2026-04",
            label: "April 2026",
            start: "2026-04-01",
            end: "2026-04-30",
            path: "month_2026-04-01_2026-04-30/metrics.json",
            source: "api",
          }],
        }),
      })),
    );
    const options = await loadReportManifest(undefined, { VITE_REPORTS_BASE_URL: "https://x/reports" });
    expect(options[0].path).toBe("https://x/reports/month_2026-04-01_2026-04-30/metrics.json");
    vi.unstubAllGlobals();
  });

  it("leaves absolute paths in manifest entries unchanged (backward compatibility)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          reports: [{
            key: "2026-03",
            label: "March 2026",
            start: "2026-03-01",
            end: "2026-03-31",
            path: "/data/reports/month_2026-03-01_2026-03-31/metrics.json",
            source: "api",
          }],
        }),
      })),
    );
    const options = await loadReportManifest(undefined, { VITE_REPORTS_BASE_URL: "https://x/reports" });
    expect(options[0].path).toBe("/data/reports/month_2026-03-01_2026-03-31/metrics.json");
    vi.unstubAllGlobals();
  });
});
