import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { InfoPopover } from "./InfoPopover";

describe("InfoPopover", () => {
  it("renders nothing for unknown info ids", () => {
    const { container } = render(<InfoPopover infoId="nope_not_here" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders a closed trigger button with the metric title in its aria-label", () => {
    render(<InfoPopover infoId="reached_an_agent" />);
    const trigger = screen.getByRole("button", { name: /About Reached an agent/i });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("dialog", { hidden: true })).toHaveAttribute("hidden");
  });

  it("opens on click and shows both content sections", async () => {
    const user = userEvent.setup();
    render(<InfoPopover infoId="reached_an_agent" />);
    await user.click(screen.getByRole("button", { name: /About Reached an agent/i }));

    expect(screen.getByRole("dialog")).not.toHaveAttribute("hidden");
    expect(screen.getByText("How it's calculated")).toBeInTheDocument();
    expect(screen.getByText("Why it matters")).toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    render(<InfoPopover infoId="reached_an_agent" />);
    await user.click(screen.getByRole("button", { name: /About Reached an agent/i }));
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { hidden: true })).toHaveAttribute("hidden");
  });

  it("closes when the close button is clicked", async () => {
    const user = userEvent.setup();
    render(<InfoPopover infoId="reached_an_agent" />);
    await user.click(screen.getByRole("button", { name: /About Reached an agent/i }));
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.getByRole("dialog", { hidden: true })).toHaveAttribute("hidden");
  });

  it("closes on outside mousedown", async () => {
    const user = userEvent.setup();
    render(
      <>
        <InfoPopover infoId="reached_an_agent" />
        <button type="button">outside</button>
      </>,
    );
    await user.click(screen.getByRole("button", { name: /About Reached an agent/i }));
    expect(screen.getByRole("dialog")).not.toHaveAttribute("hidden");

    await user.click(screen.getByRole("button", { name: "outside" }));
    expect(screen.getByRole("dialog", { hidden: true })).toHaveAttribute("hidden");
  });
});
