"use client";

import { useMemo } from "react";
import type { Finding, Scores } from "@/lib/api-client";
import { useMotionPreference } from "@/components/layout/MotionProvider";

const baseScores: Array<[keyof Scores, string, string]> = [
  ["profileStrength", "Profile", "#d69a43"],
  ["projectDepth", "Depth", "#66e2ce"],
  ["commitConsistency", "Cadence", "#ed7967"],
  ["techDiversity", "Stack", "#95b9ff"]
];
const rankScore: [keyof Scores, string, string] = ["percentileBenchmark", "Rank", "#b6df78"];

export default function ScoreScene({
  scores,
  username,
  schemaVersion,
  percentileColdStart = false
}: {
  scores: Scores;
  username: string;
  schemaVersion: number;
  findings?: Finding[];
  percentileColdStart?: boolean;
}): JSX.Element {
  const { motionEnabled } = useMotionPreference();
  const orderedScores = useMemo(() => percentileColdStart ? baseScores : [...baseScores, rankScore], [percentileColdStart]);
  const signature = orderedScores.map(([key]) => scores[key]).join("-");

  const ariaLabel = "Readable score field";

  return (
    <section
      className="score-visual"
      aria-label={ariaLabel}
      data-testid="score-scene"
      data-score-signature={signature}
      data-motion={motionEnabled ? "animated" : "static"}
      data-profile={username}
      data-schema-version={schemaVersion}
    >
      <div className="score-visual-header">
        <div>
          <span className="section-kicker">Signal topology</span>
          <h2>Where the profile holds.</h2>
        </div>
        <span className="scene-status"><span /> Readable fallback</span>
      </div>
      <div className="score-scene-stage">
        <div className="scene-canvas-shell" data-testid="score-canvas">
          <FallbackBars scores={scores} orderedScores={orderedScores} />
        </div>
        <div className="scene-grid-lines" aria-hidden="true" />
      </div>
      <div className="score-visual-labels">
        {orderedScores.map(([key, label, color]) => (
          <div key={key}>
            <span>{label}</span>
            <strong style={{ color }}>{scores[key]}</strong>
          </div>
        ))}
      </div>
      <p className="scene-caption">Evidence-backed dimensions, plotted as a field instead of flattened into a single grade.</p>
    </section>
  );
}

function FallbackBars({
  scores,
  orderedScores
}: {
  scores: Scores;
  orderedScores: Array<[keyof Scores, string, string]>;
}): JSX.Element {
  return (
    <div className="scene-fallback-bars" role="img" aria-label="Score field fallback visualization">
      {orderedScores.map(([key, label, color], index) => (
        <div className="fallback-bar-row" key={key}>
          <span>{label}</span>
          <div className="fallback-bar-track"><i style={{ width: `${scores[key]}%`, background: color, animationDelay: `${index * 120}ms` }} /></div>
          <strong>{scores[key]}</strong>
        </div>
      ))}
    </div>
  );
}
