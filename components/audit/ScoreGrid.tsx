import type { Scores } from "@/lib/api-client";

const scoreLabels: Array<[Exclude<keyof Scores, "percentileBenchmark">, string]> = [
  ["profileStrength", "Profile"],
  ["projectDepth", "Depth"],
  ["commitConsistency", "Consistency"],
  ["techDiversity", "Tech"]
];

/** Displays the four score dimensions plus the cohort-rank status. */
export function ScoreGrid({
  scores,
  percentileSampleSize,
  percentileColdStart
}: {
  scores: Scores;
  percentileSampleSize: number;
  percentileColdStart: boolean;
}): JSX.Element {
  const hasCohortRank = !percentileColdStart;

  return (
    <section className="double-bezel-shell score-panel-wrapper" aria-label="Audit score breakdown">
      <div className="double-bezel-core score-panel" style={{ padding: "20px" }}>
        <div className="score-grid">
          {scoreLabels.map(([key, label]) => (
            <div className="score-tile" key={key}>
              <div className="muted score-label">{label}</div>
              <div className="score-value">{scores[key]}</div>
            </div>
          ))}
          <div className="score-tile percentile-tile">
            <div className="muted score-label">Cohort rank</div>
            {hasCohortRank ? (
              <div className="score-value">
                {scores.percentileBenchmark}
                <span className="score-suffix">%</span>
              </div>
            ) : (
              <div className="score-value score-value-unavailable" aria-label="Not enough comparable profiles yet">
                N/A
              </div>
            )}
            <p className="score-context">
              {hasCohortRank
                ? `Ahead of ${scores.percentileBenchmark}% of developers with similar account age`
                : "Not enough comparable profiles yet."}
            </p>
            {percentileColdStart && (
              <span className="cold-start-caveat">
                {percentileSampleSize} comparable {percentileSampleSize === 1 ? "profile" : "profiles"} so far. Rank appears after the cohort is large enough.
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
