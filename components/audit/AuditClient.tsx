"use client";

import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { AuditResult, RoastIntensity } from "@/lib/api-client";
import { ApiError, requestAudit } from "@/lib/api-client";
import { AuditResultView } from "./AuditResultView";
import { OptOutControl } from "./OptOutControl";
import { RoastIntensityTabs } from "./RoastIntensityTabs";

const ScoreScene = dynamic(() => import("@/components/three/ScoreScene"), {
  ssr: false,
  loading: () => <section className="panel score-visual-loading"><span className="muted">Loading score field...</span></section>
});

/** Client-side audit runner used only after the server cache-read path has rendered immediately. */
export function AuditClient({ username, initialAudit }: { username: string; initialAudit: AuditResult | null }): JSX.Element {
  const [intensity, setIntensity] = useState<RoastIntensity>(initialAudit?.roastIntensityRequested ?? "medium");
  const initialMatchesIntensity = initialAudit?.roastIntensityRequested === intensity;
  const query = useQuery({
    queryKey: ["audit", username, intensity],
    queryFn: () => requestAudit(username, intensity),
    enabled: !initialMatchesIntensity,
    retry: (failureCount, error) => (
      failureCount < 1 && (!(error instanceof ApiError) || error.status >= 500)
    )
  });
  const audit = initialMatchesIntensity ? initialAudit : query.data ?? initialAudit;
  const errorMessage = query.isError ? auditErrorMessage(query.error) : null;
  const optedOut = query.error instanceof ApiError && (
    query.error.status === 409 || query.error.code === "opted_out"
  );

  return (
    <div className="grid">
      <section className="panel audit-header">
        <div className="audit-header-row">
          <div>
            <h1 className="audit-title">{username}</h1>
            <p className="muted audit-subtitle">
              {audit ? `Applied intensity: ${audit.roastIntensityApplied}` : "Preparing audit"}
              {query.isFetching && audit ? " - Updating roast" : ""}
            </p>
          </div>
          <RoastIntensityTabs value={intensity} onChange={setIntensity} disabled={query.isFetching} />
        </div>
      </section>

      {errorMessage ? (
        <>
          <section className="panel alert-panel" role="alert">
            <span>{errorMessage}</span>
            <button className="button" type="button" onClick={() => void query.refetch()}>
              Retry
            </button>
          </section>
          {optedOut ? <OptOutControl username={username} initialOptedOut /> : null}
        </>
      ) : null}

      {audit ? (
        <AuditResultView
          audit={audit}
          visual={<ScoreScene scores={audit.scores} username={audit.username} schemaVersion={audit.schemaVersion} findings={audit.findings} />}
        />
      ) : (
        <section className="panel empty-panel">
          <p className="muted flush">
            Audit is running. This page will update when the backend returns.
          </p>
        </section>
      )}
    </div>
  );
}

function auditErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "The audit could not be generated right now.";
  }
  if (error.status === 404) {
    return "That GitHub profile could not be found.";
  }
  if (error.status === 409 || error.code === "opted_out") {
    return "This GitHub user has opted out of GitRoast.";
  }
  if (error.status === 422) {
    return "That GitHub username or profile link is invalid.";
  }
  if (error.status === 429) {
    return "Too many audit requests were made from this connection. Try again later.";
  }
  if (error.status === 503 || error.code === "github_unavailable") {
    return "GitHub is temporarily unavailable. Retry in a moment.";
  }
  return error.message || "The audit could not be generated right now.";
}
