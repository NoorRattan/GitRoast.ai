import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MotionProvider, useMotionPreference } from "./MotionProvider";

function Probe(): JSX.Element {
  const { motionEnabled, toggleMotion } = useMotionPreference();
  return (
    <button type="button" aria-pressed={motionEnabled} onClick={toggleMotion}>
      {motionEnabled ? "Reduce motion" : "Enable motion"}
    </button>
  );
}

beforeEach(() => {
  window.localStorage.clear();
  window.matchMedia = vi.fn().mockReturnValue({
    matches: true,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn()
  });
  document.documentElement.removeAttribute("data-motion");
});

describe("MotionProvider", () => {
  it("defaults motion to ON and allows users to toggle motion preference", async () => {
    render(
      <MotionProvider>
        <Probe />
      </MotionProvider>
    );

    const toggle = await screen.findByRole("button", { name: "Reduce motion" });
    fireEvent.click(toggle);

    await waitFor(() => expect(screen.getByRole("button", { name: "Enable motion" })).toBeInTheDocument());
    expect(document.documentElement).toHaveAttribute("data-motion", "off");
    expect(window.localStorage.getItem("motion-override")).toBe("off");
  });
});
