"use client";

import { Canvas } from "@react-three/fiber";
import { useEffect, useMemo, useState } from "react";
import type { Scores } from "@/lib/api-client";
import { buildCardImageUrl } from "@/lib/api-client";

const orderedScores: Array<[keyof Scores, string, string]> = [
  ["profileStrength", "Profile", "#e2b766"],
  ["projectDepth", "Depth", "#69c5b8"],
  ["commitConsistency", "Cadence", "#f0786b"],
  ["techDiversity", "Stack", "#8ab4f8"],
  ["percentileBenchmark", "Rank", "#a3d977"]
];

/** Props-driven React Three Fiber shell for audit score visualization. */
export default function ScoreScene({ scores, username, schemaVersion }: { scores: Scores; username: string; schemaVersion: number }): JSX.Element {
  const reducedMotion = usePrefersReducedMotion();
  const imageUrl = buildCardImageUrl(username, schemaVersion);
  const signature = orderedScores.map(([key]) => scores[key]).join("-");

  if (reducedMotion) {
    return <FallbackImage username={username} imageUrl={imageUrl} />;
  }

  return (
    <section className="panel" aria-label="Score visualization" data-testid="score-scene" data-score-signature={signature} style={{ height: 320, overflow: "hidden" }}>
      <Canvas camera={{ position: [0, 0, 7], fov: 50 }}>
        <ambientLight intensity={0.85} />
        <pointLight position={[3, 3, 4]} intensity={1.2} />
        <group position={[-2.4, -1.1, 0]}>
          {orderedScores.map(([key, label, color], index) => (
            <ScoreColumn key={key} index={index} value={scores[key]} label={label} color={color} />
          ))}
        </group>
      </Canvas>
      <noscript>
        <FallbackImage username={username} imageUrl={imageUrl} />
      </noscript>
    </section>
  );
}

function ScoreColumn({ index, value, label, color }: { index: number; value: number; label: string; color: string }): JSX.Element {
  const height = Math.max(value / 28, 0.25);
  const position = useMemo<[number, number, number]>(() => [index * 1.2, height / 2, 0], [height, index]);
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[0.58, height, 0.58]} />
        <meshStandardMaterial color={color} roughness={0.48} />
      </mesh>
      <HtmlLabel label={`${label} ${value}`} y={height / 2 + 0.25} />
    </group>
  );
}

function HtmlLabel({ label, y }: { label: string; y: number }): JSX.Element {
  return (
    <mesh position={[0, y, 0]}>
      <boxGeometry args={[0.01, 0.01, 0.01]} />
      <meshBasicMaterial transparent opacity={0} />
    </mesh>
  );
}

function FallbackImage({ username, imageUrl }: { username: string; imageUrl: string }): JSX.Element {
  return (
    <section className="panel" data-testid="score-fallback" style={{ padding: 12 }}>
      <img src={imageUrl} alt={`${username} static audit card`} width={1200} height={630} style={{ width: "100%", height: "auto", borderRadius: 8 }} />
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
