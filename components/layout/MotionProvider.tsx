"use client";

import { createContext, useContext, useMemo } from "react";

type MotionPreference = {
  motionEnabled: boolean;
  ready: boolean;
  override: "on";
  toggleMotion: () => void;
};

const MotionPreferenceContext = createContext<MotionPreference | null>(null);

/** MotionProvider — keeps motion permanently enabled across the application. */
export function MotionProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const value = useMemo<MotionPreference>(() => ({
    motionEnabled: true,
    ready: true,
    override: "on",
    toggleMotion: () => {}
  }), []);

  return <MotionPreferenceContext.Provider value={value}>{children}</MotionPreferenceContext.Provider>;
}

export function useMotionPreference(): MotionPreference {
  const value = useContext(MotionPreferenceContext);
  if (!value) throw new Error("useMotionPreference must be used inside MotionProvider");
  return value;
}
