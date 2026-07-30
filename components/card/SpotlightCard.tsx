"use client";

import { MouseEvent, useRef } from "react";

type SpotlightCardProps = {
  children: React.ReactNode;
  className?: string;
  as?: React.ElementType;
  [key: string]: any;
};

export function SpotlightCard({
  children,
  className = "",
  as: Component = "div",
  ...props
}: SpotlightCardProps): JSX.Element {
  const cardRef = useRef<HTMLElement | null>(null);

  function handleMouseMove(event: MouseEvent<HTMLElement>) {
    const card = cardRef.current;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    card.style.setProperty("--mx", `${x}px`);
    card.style.setProperty("--my", `${y}px`);
  }

  return (
    <Component
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className={`spotlight-card ${className}`}
      {...props}
    >
      <div className="spotlight-glow" aria-hidden="true" />
      <div className="spotlight-content" style={{ position: "relative", zIndex: 1, height: "100%" }}>
        {children}
      </div>
    </Component>
  );
}
