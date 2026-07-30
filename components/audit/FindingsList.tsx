import { ArrowUpRight } from "lucide-react";
import type { Finding } from "@/lib/api-client";

const labels: Record<Finding["contributesTo"], string> = { profileStrength: "Profile", projectDepth: "Depth", commitConsistency: "Cadence", techDiversity: "Stack" };

export function FindingsList({ findings }: { findings: Finding[] }): JSX.Element {
  return (
    <section className="findings-panel" aria-labelledby="findings-title">
      <div className="section-heading"><div><p className="section-kicker">Scoring evidence</p><h2 id="findings-title">Why these signals moved.</h2></div><span className="evidence-count">{findings.length} signals</span></div>
      <ol className="findings-timeline">
        {findings.map((finding, index) => <li key={`${finding.metric}-${finding.contributesTo}`}><span className="timeline-marker">0{index + 1}</span><div><div className="finding-meta"><span>{labels[finding.contributesTo]}</span><ArrowUpRight size={14} aria-hidden="true" /></div><p>{finding.detail}</p></div></li>)}
      </ol>
    </section>
  );
}
