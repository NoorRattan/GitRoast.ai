import type { Finding } from "@/lib/api-client";

const labels: Record<Finding["contributesTo"], string> = {
  profileStrength: "Profile",
  projectDepth: "Depth",
  commitConsistency: "Cadence",
  techDiversity: "Stack"
};

export function FindingsList({ findings }: { findings: Finding[] }): JSX.Element {
  return (
    <section className="panel findings-panel" aria-labelledby="findings-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Scoring evidence</p>
          <h2 id="findings-title">Why these scores moved</h2>
        </div>
        <span className="evidence-count">{findings.length} signals</span>
      </div>
      <ul className="findings-list">
        {findings.map((finding) => (
          <li key={`${finding.metric}-${finding.contributesTo}`}>
            <span className="finding-tag">{labels[finding.contributesTo]}</span>
            <span>{finding.detail}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
