"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

type MotionOverride = "on" | "off";

type MotionPreference = {
  motionEnabled: boolean;
  ready: boolean;
  override: MotionOverride;
  toggleMotion: () => void;
};

const STORAGE_KEY = "motion-override";
const MotionPreferenceContext = createContext<MotionPreference | null>(null);

export function MotionProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [override, setOverride] = useState<MotionOverride>("on");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      // Storage can be unavailable in private browsing contexts.
    }
    const nextOverride: MotionOverride = stored === "off" ? "off" : "on";

    setOverride(nextOverride);
    setReady(true);
  }, []);

  const motionEnabled = override === "on";

  useEffect(() => {
    if (!ready) return;
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
