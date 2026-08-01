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
    <div className="audit-report-layout">
      <div className="audit-report-main">
        {audit.intensityDowngraded && audit.flags.beginnerAccount ? (
          <div className="downgrade-notice" role="status">
            Brutal and Hell are capped at Medium for beginner or low-activity accounts.
          </div>
        ) : null}
        <ScoreGrid
          scores={audit.scores}
          percentileSampleSize={audit.percentileSampleSize}
          percentileColdStart={audit.percentileColdStart}
        />
        {audit.findings.length > 0 && <FindingsList findings={audit.findings} />}
        <section className="roast-panel" aria-label="Roast verdict">
          <div className="roast-label"><span className="section-kicker">The verdict</span><span>{audit.reportContext?.roastTone ?? "Local roast engine"}</span></div>
          <p className="roast-copy">{audit.roastText}</p>
        </section>
        <section className="fact-grid">
          <FactList title="Strengths" items={audit.strengths} />
          <FactList title="Next fixes" items={audit.improvementAreas} />
        </section>
        <section className="roadmap-panel">
          <div className="roadmap-heading"><div><span className="section-kicker">The next four weeks</span><h2>Roadmap</h2></div><span className="roadmap-line" /></div>
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
      <aside className="audit-aside">
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
