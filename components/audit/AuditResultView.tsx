import type { AuditResult } from "@/lib/api-client";
import { ShareCard } from "@/components/card/ShareCard";
import { ScoreGrid } from "./ScoreGrid";

type AuditResultViewProps = {
  audit: AuditResult;
  visual: React.ReactNode;
};

/** Renders a completed audit response without making backend calls. */
export function AuditResultView({ audit, visual }: AuditResultViewProps): JSX.Element {
  return (
    <div className="grid two">
      <div className="grid">
        {audit.intensityDowngraded && audit.flags.beginnerAccount ? (
          <div className="panel" role="status" style={{ padding: 14, borderColor: "var(--accent)" }}>
            Brutal and Hell are capped at Medium for beginner or low-activity accounts.
          </div>
        ) : null}
        <ScoreGrid scores={audit.scores} />
        <section className="panel" style={{ padding: 18 }}>
          <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, marginTop: 0 }}>{audit.roastText}</p>
        </section>
        <section className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
          <FactList title="Strengths" items={audit.strengths} />
          <FactList title="Next fixes" items={audit.improvementAreas} />
        </section>
        <section className="panel" style={{ padding: 18 }}>
          <h2>Roadmap</h2>
          <ol style={{ display: "grid", gap: 12, paddingLeft: 20 }}>
            {audit.roadmap.map((item) => (
              <li key={`${item.week}-${item.focus}`}>
                <strong>Week {item.week}: {item.focus}</strong>
                <ul>
                  {item.actions.map((action) => <li key={action}>{action}</li>)}
                </ul>
              </li>
            ))}
          </ol>
        </section>
      </div>
      <aside className="grid" style={{ alignContent: "start" }}>
        <noscript>
          <ShareCard username={audit.username} schemaVersion={audit.schemaVersion} />
        </noscript>
        {visual}
        <ShareCard username={audit.username} schemaVersion={audit.schemaVersion} />
      </aside>
    </div>
  );
}

function FactList({ title, items }: { title: string; items: string[] }): JSX.Element {
  return (
    <section className="panel" style={{ padding: 18 }}>
      <h2>{title}</h2>
      <ul style={{ paddingLeft: 20 }}>
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </section>
  );
}
