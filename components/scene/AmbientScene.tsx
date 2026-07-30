"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useMotionPreference } from "@/components/layout/MotionProvider";
import { SceneErrorBoundary } from "./SceneErrorBoundary";

const AmbientSceneCanvas = dynamic(() => import("./AmbientSceneCanvas"), { ssr: false });

export function AmbientScene(): JSX.Element {
  const [available, setAvailable] = useState(false);
  const { motionEnabled } = useMotionPreference();

  useEffect(() => {
    try {
      const canvas = document.createElement("canvas");
      setAvailable(typeof window.WebGLRenderingContext !== "undefined" && Boolean(canvas.getContext("webgl")));
    } catch {
      setAvailable(false);
    }
  }, []);

  return (
    <div className="ambient-scene" aria-hidden="true">
      <div className="ambient-halo" />
      {available && motionEnabled ? (
        <SceneErrorBoundary fallback={null} onError={() => setAvailable(false)}>
          <AmbientSceneCanvas />
        </SceneErrorBoundary>
      ) : null}
    </div>
  );
}
