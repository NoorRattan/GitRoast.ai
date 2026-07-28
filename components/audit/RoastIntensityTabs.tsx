"use client";

import type { RoastIntensity } from "@/lib/api-client";

const intensities: RoastIntensity[] = ["mild", "medium", "brutal", "hell"];

/** Lets the user choose the requested roast intensity before the client-side audit POST runs. */
export function RoastIntensityTabs({
  value,
  onChange,
  disabled
}: {
  value: RoastIntensity;
  onChange: (value: RoastIntensity) => void;
  disabled?: boolean;
}): JSX.Element {
  return (
    <div className="intensity-tabs" role="tablist" aria-label="Roast intensity">
      {intensities.map((intensity) => (
        <button
          key={intensity}
          type="button"
          role="tab"
          aria-selected={value === intensity}
          className={`button${value === intensity ? " primary" : ""}`}
          disabled={disabled}
          onClick={() => onChange(intensity)}
        >
          {intensity}
        </button>
      ))}
    </div>
  );
}
