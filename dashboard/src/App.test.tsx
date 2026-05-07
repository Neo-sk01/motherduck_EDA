import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import fixture from "./fixtures/april-2026-metrics.json";

describe("App", () => {
  beforeEach(() => {
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
    expect(screen.getAllByText(/98.8%/).length).toBeGreaterThan(0);
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

  it("shows cross-queue reference rows", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click((await screen.findAllByRole("button", { name: "Cross Queue" }))[0]);

    expect(screen.getByText("Gabriel Hubert 299")).toBeInTheDocument();
    expect(screen.getByText("9052833500 63")).toBeInTheDocument();
    expect(screen.getAllByText("Gabriel Hubert").length).toBeGreaterThan(0);
    expect(screen.getAllByText("299").length).toBeGreaterThan(0);
    expect(screen.getAllByText("9052833500").length).toBeGreaterThan(0);
    expect(screen.getAllByText("63").length).toBeGreaterThan(0);
  });

  it("shows funnel detail routing values", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click((await screen.findAllByRole("button", { name: "Funnel Detail" }))[0]);

    expect(screen.getAllByText(/98.8%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/88.2%/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Primary Failed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unaccounted").length).toBeGreaterThan(0);
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
});
