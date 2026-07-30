"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const AmbientSceneCanvas = dynamic(() => import("./AmbientSceneCanvas"), { ssr: false });

export function AmbientScene(): JSX.Element {
  const [available, setAvailable] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(media.matches);
    const onChange = () => setReducedMotion(media.matches);
    media.addEventListener("change", onChange);
    try {
      const canvas = document.createElement("canvas");
      setAvailable(typeof window.WebGLRenderingContext !== "undefined" && Boolean(canvas.getContext("webgl")));
    } catch {
      setAvailable(false);
    }
    return () => media.removeEventListener("change", onChange);
  }, []);

  return (
    <div className="ambient-scene" aria-hidden="true">
      <div className="ambient-halo" />
      {available && !reducedMotion ? <AmbientSceneCanvas /> : null}
    </div>
  );
}
