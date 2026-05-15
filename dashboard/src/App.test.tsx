import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import fixture from "./fixtures/april-2026-metrics.json";

const TUTORIAL_STORAGE_KEY = "csh-platform-tutorial-complete";

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    installLocalStorageMock();
    window.localStorage.setItem(TUTORIAL_STORAGE_KEY, "true");
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => fixture,
    })));
  });

  it("renders the shell and April overview reference numbers", async () => {
    render(<App />);

    expect(await screen.findByText("NeoLore Queue Analytics")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Per Queue" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cross Queue" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Funnel Detail" })).toBeInTheDocument();
    expect(await screen.findByText(/2026-04-01 through 2026-04-30/)).toBeInTheDocument();
    expect(screen.getAllByText("1,181").length).toBeGreaterThan(0);
    expect(screen.getAllByText("66").length).toBeGreaterThan(0);
    expect(screen.getAllByText("343").length).toBeGreaterThan(0);
    expect(screen.getAllByText("30").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/98.3%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/84.7%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/88.2%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/87.9%/).length).toBeGreaterThan(0);
  });

  it("opens per queue from a queue card", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("CSR French");
    await user.click(screen.getAllByRole("button", { name: /CSR French/i })[0]);

    expect(screen.getByRole("heading", { name: "CSR French" })).toBeInTheDocument();
    expect(screen.getByText(/8021 · French · primary/)).toBeInTheDocument();
  });

  it("walks first-time users through the dashboard views", async () => {
    const user = userEvent.setup();
    window.localStorage.removeItem(TUTORIAL_STORAGE_KEY);
    render(<App />);

    expect(
      await screen.findByRole("dialog", { name: "CSH platform guide" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Period Health" })).toBeInTheDocument();
    expect(screen.getByText(/Start with the health snapshot/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByRole("heading", { name: "CSR English" })).toBeInTheDocument();
    expect(screen.getByText(/Pick an individual queue/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByRole("heading", { name: "Cross Queue Analytics" })).toBeInTheDocument();
    expect(screen.getByText(/Compare agents and callers/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByRole("heading", { name: "Funnel Detail" })).toBeInTheDocument();
    expect(screen.getByText(/Use funnel detail/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Finish" }));

    expect(screen.queryByRole("dialog", { name: "CSH platform guide" })).not.toBeInTheDocument();
    expect(window.localStorage.getItem(TUTORIAL_STORAGE_KEY)).toBe("true");
  });

  it("keeps completed tutorials closed but lets users reopen them", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("NeoLore Queue Analytics")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "CSH platform guide" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open tutorial" }));

    expect(screen.getByRole("dialog", { name: "CSH platform guide" })).toBeInTheDocument();
    expect(screen.getByText(/Start with the health snapshot/i)).toBeInTheDocument();
  });

  it("shows cross-queue reference rows", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click((await screen.findAllByRole("button", { name: "Cross Queue" }))[0]);

    expect(screen.getByText("Alicia Yameen 241")).toBeInTheDocument();
    expect(screen.getByText("9052833500 63")).toBeInTheDocument();
    expect(screen.getAllByText("Alicia Yameen").length).toBeGreaterThan(0);
    expect(screen.getAllByText("241").length).toBeGreaterThan(0);
    expect(screen.getAllByText("9052833500").length).toBeGreaterThan(0);
    expect(screen.getAllByText("63").length).toBeGreaterThan(0);
  });

  it("shows funnel detail routing values", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click((await screen.findAllByRole("button", { name: "Funnel Detail" }))[0]);

    expect(screen.getAllByText(/98.3%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/88.2%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Primary Failed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unaccounted").length).toBeGreaterThan(0);
  });

  it("toggles funnel card scrolling from the overview", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "French Funnel" });
    const scrollToggles = screen.getAllByRole("checkbox", { name: /Scroll/i });
    expect(scrollToggles).toHaveLength(2);
    expect(scrollToggles[1]).not.toBeChecked();

    await user.click(scrollToggles[1]);

    expect(scrollToggles[1]).toBeChecked();
  });

  it("can sort a visible cross-queue table", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click((await screen.findAllByRole("button", { name: "Cross Queue" }))[0]);
    const table = screen.getAllByRole("table")[0];
    const firstBody = within(table).getAllByRole("row")[1].textContent;
    await user.click(within(table).getByRole("button", { name: /Agent/i }));

    await waitFor(() => {
      expect(within(table).getAllByRole("row")[1].textContent).not.toBe(firstBody);
    });
  });

  it("switches reports from the monthly manifest", async () => {
    const user = userEvent.setup();
    const marchFixture = structuredClone(fixture);
    marchFixture.date_range = { start: "2026-03-01", end: "2026-03-31" };
    marchFixture.queues["8020"].total_calls = 777;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/data/reports/manifest.json")) {
        return {
          ok: true,
          json: async () => ({
            reports: [
              {
                key: "2026-04",
                label: "April 2026",
                start: "2026-04-01",
                end: "2026-04-30",
                path: "/data/reports/month_2026-04-01_2026-04-30/metrics.json",
                source: "csv",
              },
              {
                key: "2026-03",
                label: "March 2026",
                start: "2026-03-01",
                end: "2026-03-31",
                path: "/data/reports/month_2026-03-01_2026-03-31/metrics.json",
                source: "api",
              },
            ],
          }),
        };
      }
      return {
        ok: true,
        json: async () => (url.includes("2026-03") ? marchFixture : fixture),
      };
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByText(/2026-04-01 through 2026-04-30/);
    await user.selectOptions(screen.getByLabelText(/Report month/i), "2026-03");

    expect(await screen.findByText(/2026-03-01 through 2026-03-31/)).toBeInTheDocument();
    expect(screen.getAllByText("777").length).toBeGreaterThan(0);
  });

  it("downloads a full CSV export for the selected report month", async () => {
    const user = userEvent.setup();
    const januaryFixture = structuredClone(fixture);
    januaryFixture.period = "2026-01";
    januaryFixture.date_range = { start: "2026-01-01", end: "2026-01-31" };
    januaryFixture.queues["8020"].total_calls = 321;
    januaryFixture.crossqueue.funnels.English.primary_calls = 321;

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/data/reports/manifest.json")) {
        return {
          ok: true,
          json: async () => ({
            reports: [
              {
                key: "2026-04",
                label: "April 2026",
                start: "2026-04-01",
                end: "2026-04-30",
                path: "/data/reports/month_2026-04-01_2026-04-30/metrics.json",
                source: "csv",
              },
              {
                key: "2026-01",
                label: "January 2026",
                start: "2026-01-01",
                end: "2026-01-31",
                path: "/data/reports/month_2026-01-01_2026-01-31/metrics.json",
                source: "api",
              },
            ],
          }),
        };
      }
      return {
        ok: true,
        json: async () => (url.includes("2026-01") ? januaryFixture : fixture),
      };
    });
    const createObjectURL = vi.fn((blob: Blob) => {
      expect(blob).toBeInstanceOf(Blob);
      return "blob:neolore-report";
    });
    const revokeObjectURL = vi.fn();
    const anchorClick = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    render(<App />);

    await screen.findByText(/2026-04-01 through 2026-04-30/);
    await user.selectOptions(screen.getByLabelText(/Report month/i), "2026-01");
    expect(await screen.findByText(/2026-01-01 through 2026-01-31/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Export CSV" }));

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(anchorClick).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:neolore-report");
    const csvBlob = createObjectURL.mock.calls[0]?.[0];
    if (!csvBlob) throw new Error("CSV Blob was not passed to createObjectURL.");
    const csv = await readBlobText(csvBlob);
    expect(csv.split("\n")[0]).toBe(
      "period,date_start,date_end,section,queue_id,queue_name,language,role,entity_type,entity,date,hour,dow,metric,value,details",
    );
    expect(csv).toContain(
      "2026-01,2026-01-01,2026-01-31,queue_summary,8020,CSR English,English,primary,queue,,,,,total_calls,321,",
    );
    expect(csv).toContain("queue_daily_volume,8020,CSR English");
    expect(csv).toContain("queue_hourly_volume,8020,CSR English");
    expect(csv).toContain("queue_agent_leaderboard,8020,CSR English");
    expect(csv).toContain("crossqueue_funnel");
    expect(csv).toContain("crossqueue_agents");
    expect(csv).toContain("anomalies");
  });
});

function readBlobText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => resolve(String(reader.result));
    reader.readAsText(blob);
  });
}

function installLocalStorageMock() {
  const store = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key) => store.get(key) ?? null,
    key: (index) => Array.from(store.keys())[index] ?? null,
    removeItem: (key) => store.delete(key),
    setItem: (key, value) => store.set(key, String(value)),
  };

  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: storage,
  });
}
