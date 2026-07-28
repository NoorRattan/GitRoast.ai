import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuditClient } from "./AuditClient";
import type { AuditResult } from "@/lib/api-client";

vi.mock("next/dynamic", () => ({
  default: () => function MockScoreScene(): JSX.Element {
    return <div data-testid="mock-scene" />;
  }
}));

const requestAudit = vi.fn();
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, requestAudit: (...args: unknown[]) => requestAudit(...args) };
});

function renderWithQuery(ui: React.ReactElement): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function audit(overrides: Partial<AuditResult> = {}): AuditResult {
  return {
    username: "newstarter",
    generatedAt: "2026-07-27T00:00:00Z",
    schemaVersion: 1,
    cacheHit: false,
    roastIntensityRequested: "hell",
    roastIntensityApplied: "medium",
    intensityDowngraded: true,
    scores: { profileStrength: 70, projectDepth: 60, commitConsistency: 50, techDiversity: 80, percentileBenchmark: 65 },
    flags: { greenSquareFarming: false, beginnerAccount: true },
    findings: [{ metric: "fork_ratio", detail: "many forks", value: 0.5, contributesTo: "profileStrength" }],
    percentileSampleSize: 8,
    percentileColdStart: true,
    roastText: "Generated roast",
    strengths: ["Real work", "Clear motion", "Useful stack"],
    improvementAreas: ["Pin better repos", "Add tests", "Write READMEs"],
    roadmap: [{ week: 1, focus: "Profile", actions: ["Pin better repos"] }],
    ...overrides
  };
}

describe("AuditClient", () => {
  beforeEach(() => {
    requestAudit.mockReset();
  });

  it("renders the lightweight shell and triggers client-side POST when no cached audit exists", async () => {
    requestAudit.mockResolvedValueOnce(audit({ intensityDowngraded: false, roastIntensityApplied: "medium", roastIntensityRequested: "medium" }));

    renderWithQuery(<AuditClient username="newstarter" initialAudit={null} />);

    expect(screen.getByText(/Audit is running/)).toBeInTheDocument();
    await waitFor(() => expect(requestAudit).toHaveBeenCalledWith("newstarter", "medium"));
    await screen.findByText("Generated roast");
  });

  it("shows the beginner downgrade explanation when the API reports it", () => {
    renderWithQuery(<AuditClient username="newstarter" initialAudit={audit()} />);

    expect(screen.getByText(/capped at Medium/)).toBeInTheDocument();
    expect(screen.getByText("many forks")).toBeInTheDocument();
    expect(screen.getByText(/8 comparable profiles/)).toBeInTheDocument();
  });

  it("requests a new roast when intensity changes from a server-provided audit", async () => {
    const initial = audit({
      roastIntensityRequested: "medium",
      roastIntensityApplied: "medium",
      intensityDowngraded: false
    });
    requestAudit.mockResolvedValueOnce(audit({
      roastIntensityRequested: "brutal",
      roastIntensityApplied: "brutal",
      intensityDowngraded: false,
      roastText: "Brutal refresh"
    }));

    renderWithQuery(<AuditClient username="newstarter" initialAudit={initial} />);
    fireEvent.click(screen.getByRole("tab", { name: "brutal" }));

    await waitFor(() => expect(requestAudit).toHaveBeenCalledWith("newstarter", "brutal"));
    expect(await screen.findByText("Brutal refresh")).toBeInTheDocument();
  });
});
