import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Tooltip } from "./Tooltip";

describe("Tooltip", () => {
  it("renders a trigger button with aria-describedby pointing at the popover", () => {
    render(<Tooltip id="t1" label="What is this?" content="A definition." />);
    const trigger = screen.getByRole("button", { name: "What is this?" });
    expect(trigger).toHaveAttribute("aria-describedby", "t1");
  });

  it("reveals the popover on hover and hides on mouse leave", async () => {
    const user = userEvent.setup();
    render(<Tooltip id="t2" label="Why" content="Because." />);
    const popover = screen.getByRole("tooltip", { hidden: true });
    expect(popover).toHaveAttribute("hidden");

    await user.hover(screen.getByRole("button", { name: "Why" }));
    expect(popover).not.toHaveAttribute("hidden");

    await user.unhover(screen.getByRole("button", { name: "Why" }));
    expect(popover).toHaveAttribute("hidden");
  });

  it("reveals the popover on focus and hides on blur", async () => {
    const user = userEvent.setup();
    render(<Tooltip id="t3" label="Why" content="Because." />);
    const popover = screen.getByRole("tooltip", { hidden: true });
    expect(popover).toHaveAttribute("hidden");

    await user.tab();
    expect(popover).not.toHaveAttribute("hidden");

    await user.tab();
    expect(popover).toHaveAttribute("hidden");
  });
});
