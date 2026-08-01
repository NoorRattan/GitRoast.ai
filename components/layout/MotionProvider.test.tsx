import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MotionProvider, useMotionPreference } from "./MotionProvider";

function Probe(): JSX.Element {
  const { motionEnabled } = useMotionPreference();
  return (
    <div>
      {motionEnabled ? "Motion enabled" : "Motion disabled"}
    </div>
  );
}

describe("MotionProvider", () => {
  it("keeps motion permanently enabled", () => {
    render(
      <MotionProvider>
        <Probe />
      </MotionProvider>
    );

    expect(screen.getByText("Motion enabled")).toBeInTheDocument();
  });
});
