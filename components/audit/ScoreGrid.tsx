import type { Scores } from "@/lib/api-client";

const scoreLabels: Array<[keyof Scores, string]> = [
  ["profileStrength", "Profile"],
  ["projectDepth", "Depth"],
  ["commitConsistency", "Consistency"],
  ["techDiversity", "Tech"],
  ["percentileBenchmark", "Percentile"]
];

/** Displays the five composite audit scores using camelCase frontend fields only. */
export function ScoreGrid({ scores }: { scores: Scores }): JSX.Element {
  return (
    <section className="panel" style={{ padding: 16 }}>
      <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" }}>
        {scoreLabels.map(([key, label]) => (
          <div key={key} style={{ background: "#111313", borderRadius: 8, padding: 12 }}>
            <div className="muted" style={{ fontSize: 13 }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 800 }}>{scores[key]}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
