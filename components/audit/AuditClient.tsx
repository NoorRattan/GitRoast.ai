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
  loading: () => <section className="score-visual score-loading"><div className="loading-orbit" aria-hidden="true"><span /><span /><span /></div><span className="section-kicker">Loading signal topology</span></section>
});

const intensityGuidance: Record<RoastIntensity, string> = {
  mild: "Constructive and encouraging",
  medium: "Direct, focused on the work",
  brutal: "Sharper criticism of public signals, never the person",
  hell: "Maximum theatrical heat aimed at the work, never the person"
};

/** Client-side audit runner used only after the server cache-read path has rendered immediately. */
export function AuditClient({ username, initialAudit }: { username: string; initialAudit: AuditResult | null }): JSX.Element {
  const [intensity, setIntensity] = useState<RoastIntensity>(initialAudit?.roastIntensityRequested ?? "medium");
  // Audits created before evidence collection existed are incomplete. Keep their
  // shell visible, but refresh them rather than treating legacy cached data as final.
  const initialMatchesIntensity = initialAudit?.roastIntensityRequested === intensity
    && Array.isArray(initialAudit.findings)
    && initialAudit.findings.length > 0;
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
    <div className="audit-flow">
      <section className="audit-header">
        <div className="audit-header-row">
          <div>
            <p className="section-kicker">Profile audit / live read</p>
            <h1 className="audit-title"><span>@</span>{username}</h1>
            <p className="audit-subtitle">
              {audit ? `Applied intensity: ${audit.roastIntensityApplied}` : "Preparing audit"}
              {query.isFetching && audit ? " · Updating roast" : " · Evidence-linked"}
              {audit ? ` \u00b7 ${audit.reportContext?.roastTone ?? intensityGuidance[intensity]} \u00b7 ${audit.reportContext?.scope ?? "Public GitHub signals only; directional, not a code review."}` : null}
            </p>
          </div>
          <div className="audit-controls"><span className="control-label">Roast intensity</span><RoastIntensityTabs value={intensity} onChange={setIntensity} disabled={query.isFetching} /></div>
        </div>
      </section>

      {errorMessage ? (
        <>
          <section className="alert-panel" role="alert">
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
          visual={(
            <ScoreScene
              scores={audit.scores}
              username={audit.username}
              schemaVersion={audit.schemaVersion}
              findings={audit.findings}
              percentileColdStart={audit.percentileColdStart}
            />
          )}
        />
      ) : !errorMessage ? (
        <AuditLoadingScreen username={username} />
      ) : null}
    </div>
  );
}

function AuditLoadingScreen({ username }: { username: string }): JSX.Element {
  return (
    <section className="audit-loading-screen" role="status" aria-live="polite" aria-label={`Preparing audit for ${username}`}>
      <div className="audit-loading-atmosphere" aria-hidden="true" />
      <div className="audit-loading-content">
        <p className="audit-loading-kicker"><span aria-hidden="true" /> Profile audit / live read</p>
        <div className="audit-lens" aria-hidden="true">
          <i className="audit-lens-ring audit-lens-ring-outer" />
          <i className="audit-lens-ring audit-lens-ring-inner" />
          <i className="audit-lens-ring audit-lens-ring-vertical" />
          <i className="audit-lens-scan" />
          <i className="audit-lens-core" />
        </div>
        <h2 className="audit-loading-username"><span>@</span>{username}</h2>
        <p className="audit-loading-subtitle">Preparing audit <b>·</b> Evidence-linked</p>
        <p className="audit-loading-message">Reading public signals and assembling the report.</p>
        <div className="audit-loading-proof" aria-label="Audit safeguards">
          <span>Public GitHub data</span>
          <span>Evidence retained</span>
          <span>Report in progress</span>
        </div>
      </div>
    </section>
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
