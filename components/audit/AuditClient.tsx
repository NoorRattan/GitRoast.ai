"use client";

import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { AuditResult, RoastIntensity } from "@/lib/api-client";
import { requestAudit } from "@/lib/api-client";
import { AuditResultView } from "./AuditResultView";
import { RoastIntensityTabs } from "./RoastIntensityTabs";

const ScoreScene = dynamic(() => import("@/components/three/ScoreScene"), {
  ssr: false,
  loading: () => <section className="panel score-visual-loading"><span className="muted">Loading score field...</span></section>
});

/** Client-side audit runner used only after the server cache-read path has rendered immediately. */
export function AuditClient({ username, initialAudit }: { username: string; initialAudit: AuditResult | null }): JSX.Element {
  const [intensity, setIntensity] = useState<RoastIntensity>(initialAudit?.roastIntensityRequested ?? "medium");
  const query = useQuery({
    queryKey: ["audit", username, intensity],
    queryFn: () => requestAudit(username, intensity),
    enabled: initialAudit === null,
    retry: 1
  });
  const audit = initialAudit ?? query.data ?? null;

  return (
    <div className="grid">
      <section className="panel audit-header">
        <div className="audit-header-row">
          <div>
            <h1 style={{ margin: 0 }}>{username}</h1>
            <p className="muted" style={{ marginBottom: 0 }}>
              {audit ? `Applied intensity: ${audit.roastIntensityApplied}` : "Preparing audit"}
            </p>
          </div>
          <RoastIntensityTabs value={intensity} onChange={setIntensity} disabled={query.isFetching} />
        </div>
      </section>

      {query.isError ? (
        <section className="panel" role="alert" style={{ padding: 16, borderColor: "var(--danger)" }}>
          The audit could not be generated right now.
        </section>
      ) : null}

      {audit ? (
        <AuditResultView
          audit={audit}
          visual={<ScoreScene scores={audit.scores} username={audit.username} schemaVersion={audit.schemaVersion} />}
        />
      ) : (
        <section className="panel" style={{ padding: 20 }}>
          <p className="muted" style={{ margin: 0 }}>
            Audit is running. This page will update when the backend returns.
          </p>
        </section>
      )}
    </div>
  );
}
