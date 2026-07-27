"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import type { Scores } from "@/lib/api-client";
import { buildCardImageUrl } from "@/lib/api-client";

const orderedScores: Array<[keyof Scores, string, string]> = [
  ["profileStrength", "Profile", "var(--accent)"],
  ["projectDepth", "Depth", "var(--accent-2)"],
  ["commitConsistency", "Cadence", "var(--danger)"],
  ["techDiversity", "Stack", "var(--blue)"],
  ["percentileBenchmark", "Rank", "var(--green)"]
];

/** Stable score visualization for the deployed audit page. */
export default function ScoreScene({ scores, username, schemaVersion }: { scores: Scores; username: string; schemaVersion: number }): JSX.Element {
  const reducedMotion = usePrefersReducedMotion();
  const imageUrl = buildCardImageUrl(username, schemaVersion);
  const signature = orderedScores.map(([key]) => scores[key]).join("-");

  if (reducedMotion) {
    return <FallbackImage username={username} imageUrl={imageUrl} />;
  }

  return (
    <section className="panel" aria-label="Score visualization" data-testid="score-scene" data-score-signature={signature} style={{ padding: 16 }}>
      <div style={{ display: "grid", gap: 14 }}>
        {orderedScores.map(([key, label, color]) => (
          <div key={key} style={{ display: "grid", gap: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <strong>{label}</strong>
              <span style={{ color }}>{scores[key]}</span>
            </div>
            <div aria-hidden="true" style={{ height: 10, borderRadius: 999, background: "#0c0d0d", overflow: "hidden" }}>
              <div style={{ width: `${Math.max(4, Math.min(100, scores[key]))}%`, height: "100%", borderRadius: 999, background: color }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function FallbackImage({ username, imageUrl }: { username: string; imageUrl: string }): JSX.Element {
  return (
    <section className="panel" data-testid="score-fallback" style={{ padding: 12 }}>
      <Image src={imageUrl} alt={`${username} static audit card`} width={1200} height={630} unoptimized style={{ width: "100%", height: "auto", borderRadius: 8 }} />
    </section>
  );
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(media.matches);
    const listener = () => setReduced(media.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);
  return reduced;
}
