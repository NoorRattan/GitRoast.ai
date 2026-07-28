import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Scores } from "@/lib/api-client";
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
    const { rerender } = render(<ScoreScene scores={scores} username="newstarter" schemaVersion={1} />);

    expect(screen.getByTestId("score-scene")).toHaveAttribute("data-score-signature", "70-60-50-80-65");
    rerender(<ScoreScene scores={{ ...scores, projectDepth: 91 }} username="newstarter" schemaVersion={1} />);
    expect(screen.getByTestId("score-scene")).toHaveAttribute("data-score-signature", "70-91-50-80-65");
  });

  it("uses the static fallback image for reduced motion", () => {
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    });

    render(<ScoreScene scores={scores} username="newstarter" schemaVersion={4} />);

    expect(screen.getByTestId("score-fallback")).toBeInTheDocument();
    expect(screen.getByAltText("newstarter static audit card")).toHaveAttribute(
      "src",
      "https://gitroast-card-preview.jnoorrattan.workers.dev/card/newstarter.png?v=4"
    );
  });
});
