"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

type MotionOverride = "system" | "on" | "off";

type MotionPreference = {
  motionEnabled: boolean;
  ready: boolean;
  override: MotionOverride;
  toggleMotion: () => void;
};

const STORAGE_KEY = "motion-override";
const MotionPreferenceContext = createContext<MotionPreference | null>(null);

export function MotionProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [systemReduced, setSystemReduced] = useState(true);
  const [override, setOverride] = useState<MotionOverride>("system");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      // Storage can be unavailable in private browsing contexts.
    }
    const nextOverride: MotionOverride = stored === "on" || stored === "off" ? stored : "system";

    setSystemReduced(media.matches);
    setOverride(nextOverride);
    setReady(true);

    const onChange = () => setSystemReduced(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const motionEnabled = ready && (override === "on" || (override === "system" && !systemReduced));

  useEffect(() => {
    if (!ready) return;
    if (override === "system") {
      document.documentElement.removeAttribute("data-motion");
      return;
    }
    document.documentElement.setAttribute("data-motion", override);
  }, [override, ready]);

  const value = useMemo<MotionPreference>(() => ({
    motionEnabled,
    ready,
    override,
    toggleMotion: () => {
      const next: MotionOverride = motionEnabled ? "off" : "on";
      setOverride(next);
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // Storage can be unavailable in private browsing contexts.
      }
      document.documentElement.setAttribute("data-motion", next);
    }
  }), [motionEnabled, override, ready]);

  return <MotionPreferenceContext.Provider value={value}>{children}</MotionPreferenceContext.Provider>;
}

export function useMotionPreference(): MotionPreference {
  const value = useContext(MotionPreferenceContext);
  if (!value) throw new Error("useMotionPreference must be used inside MotionProvider");
  return value;
}
