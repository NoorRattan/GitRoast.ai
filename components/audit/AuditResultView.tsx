import type { AuditResult } from "@/lib/api-client";
import { ShareCard } from "@/components/card/ShareCard";
import { FindingsList } from "./FindingsList";
import { OptOutControl } from "./OptOutControl";
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
          <div className="panel downgrade-notice" role="status">
            Brutal and Hell are capped at Medium for beginner or low-activity accounts.
          </div>
        ) : null}
        <ScoreGrid
          scores={audit.scores}
          percentileSampleSize={audit.percentileSampleSize}
          percentileColdStart={audit.percentileColdStart}
        />
        <FindingsList findings={audit.findings} />
        <section className="panel roast-panel" aria-label="Roast verdict">
          <p>{audit.roastText}</p>
        </section>
        <section className="grid fact-grid">
          <FactList title="Strengths" items={audit.strengths} />
          <FactList title="Next fixes" items={audit.improvementAreas} />
        </section>
        <section className="panel roadmap-panel">
          <h2>Roadmap</h2>
          <ol className="roadmap-list">
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
        <OptOutControl username={audit.username} />
      </div>
      <aside className="grid audit-aside">
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
    <section className="panel fact-panel">
      <h2>{title}</h2>
      <ul>
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </section>
  );
}
