"use client";

import type { RoastIntensity } from "@/lib/api-client";

const intensities: RoastIntensity[] = ["mild", "medium", "brutal", "hell"];

export function RoastIntensityTabs({ value, onChange, disabled }: { value: RoastIntensity; onChange: (value: RoastIntensity) => void; disabled?: boolean }): JSX.Element {
  return (
    <div className="intensity-tabs" role="tablist" aria-label="Roast intensity">
      {intensities.map((intensity) => <button key={intensity} type="button" role="tab" aria-selected={value === intensity} className={value === intensity ? "is-selected" : ""} disabled={disabled} onClick={() => onChange(intensity)}>{intensity}</button>)}
    </div>
  );
}
