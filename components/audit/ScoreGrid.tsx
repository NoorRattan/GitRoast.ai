import type { Scores } from "@/lib/api-client";

const scoreLabels: Array<[Exclude<keyof Scores, "percentileBenchmark">, string]> = [
  ["profileStrength", "Profile"],
  ["projectDepth", "Depth"],
  ["commitConsistency", "Consistency"],
  ["techDiversity", "Tech"]
];

/** Displays the five composite audit scores using camelCase frontend fields only. */
export function ScoreGrid({
  scores,
  percentileSampleSize,
  percentileColdStart
}: {
  scores: Scores;
  percentileSampleSize: number;
  percentileColdStart: boolean;
}): JSX.Element {
  return (
    <section className="panel score-panel" aria-label="Audit score breakdown">
      <div className="score-grid">
        {scoreLabels.map(([key, label]) => (
          <div className="score-tile" key={key}>
            <div className="muted score-label">{label}</div>
            <div className="score-value">{scores[key]}</div>
          </div>
        ))}
        <div className="score-tile percentile-tile">
          <div className="muted score-label">Cohort rank</div>
          <div className="score-value">
            {percentileColdStart && (
              <span className="score-provisional" aria-label="provisional">~</span>
            )}
            {scores.percentileBenchmark}
            <span className="score-suffix">%</span>
          </div>
          <p className="score-context">
            {percentileColdStart
              ? `Ahead of ${scores.percentileBenchmark}% of ${percentileSampleSize} comparable ${percentileSampleSize === 1 ? "profile" : "profiles"} — provisional`
              : `Ahead of ${scores.percentileBenchmark}% of developers with similar account age`}
          </p>
          {percentileColdStart && (
            <span className="cold-start-caveat">
              Based on a small, growing sample — this rank may shift as more profiles are compared.
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
