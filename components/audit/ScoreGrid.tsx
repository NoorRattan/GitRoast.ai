import type { Scores } from "@/lib/api-client";

const scoreLabels: Array<[Exclude<keyof Scores, "percentileBenchmark">, string, string]> = [
  ["profileStrength", "Profile", "The visible surface"],
  ["projectDepth", "Depth", "Proof of real work"],
  ["commitConsistency", "Cadence", "Evidence of upkeep"],
  ["techDiversity", "Stack", "Range without noise"]
];

export function ScoreGrid({ scores, percentileSampleSize, percentileColdStart }: { scores: Scores; percentileSampleSize: number; percentileColdStart: boolean }): JSX.Element {
  const hasCohortRank = !percentileColdStart;
  return (
    <section className="score-panel" aria-label="Audit score breakdown">
      <div className="score-panel-heading"><div><span className="section-kicker">The readout</span><h2>Four signals. One direction.</h2></div><span className="score-panel-rule" /></div>
      <div className="score-matrix">
        {scoreLabels.map(([key, label, detail], index) => <div className="score-metric" key={key}><span className="metric-index">0{index + 1}</span><div><span>{label}</span><small>{detail}</small></div><strong>{scores[key]}</strong></div>)}
        <div className="score-metric rank-metric"><span className="metric-index">05</span><div><span>Cohort rank</span><small>{hasCohortRank ? `Ahead of ${scores.percentileBenchmark}% of similar profiles` : "Not enough comparable profiles yet."}</small></div>{hasCohortRank ? <strong>{scores.percentileBenchmark}<small>%</small></strong> : <strong aria-label="Not enough comparable profiles yet">N/A</strong>}{percentileColdStart ? <em>{percentileSampleSize} comparable {percentileSampleSize === 1 ? "profile" : "profiles"} so far</em> : null}</div>
      </div>
    </section>
  );
}
