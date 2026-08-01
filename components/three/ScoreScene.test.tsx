import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Scores } from "@/lib/api-client";
import { MotionProvider } from "@/components/layout/MotionProvider";
import ScoreScene from "./ScoreScene";

const scores: Scores = {
  profileStrength: 70,
  projectDepth: 60,
  commitConsistency: 50,
  techDiversity: 80,
  percentileBenchmark: 65
};

beforeEach(() => {
  window.matchMedia = vi.fn().mockReturnValue({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn()
  });
});

describe("ScoreScene", () => {
  it("updates its score signature when score props change", () => {
    const { rerender } = render(<MotionProvider><ScoreScene scores={scores} username="newstarter" schemaVersion={1} /></MotionProvider>);

    expect(screen.getByTestId("score-scene")).toHaveAttribute("data-score-signature", "70-60-50-80-65");
    rerender(<MotionProvider><ScoreScene scores={{ ...scores, projectDepth: 91 }} username="newstarter" schemaVersion={1} /></MotionProvider>);
    expect(screen.getByTestId("score-scene")).toHaveAttribute("data-score-signature", "70-91-50-80-65");
  });

  it("omits the rank score when the cohort is still cold-starting", () => {
    render(<MotionProvider><ScoreScene scores={scores} username="newstarter" schemaVersion={1} percentileColdStart /></MotionProvider>);

    expect(screen.getByTestId("score-scene")).toHaveAttribute("data-score-signature", "70-60-50-80");
    expect(screen.queryByText("Rank")).not.toBeInTheDocument();
  });

  it("keeps motion active by default", () => {
    render(<MotionProvider><ScoreScene scores={scores} username="newstarter" schemaVersion={4} /></MotionProvider>);

    expect(screen.getByTestId("score-scene")).toHaveAttribute("data-motion", "animated");
    expect(screen.getByTestId("score-canvas")).toBeInTheDocument();
  });
});
