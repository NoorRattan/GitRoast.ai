"use client";

import React, { useRef, useState, useEffect } from "react";

type MagneticProps = {
  children: React.ReactElement;
  range?: number;
};

export function Magnetic({ children, range = 45 }: MagneticProps): JSX.Element {
  const ref = useRef<HTMLElement | null>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const handleMouseMove = (event: MouseEvent) => {
      const { clientX, clientY } = event;
      const { left, top, width, height } = element.getBoundingClientRect();
      const centerX = left + width / 2;
      const centerY = top + height / 2;

      const distanceX = clientX - centerX;
      const distanceY = clientY - centerY;
      const distance = Math.hypot(distanceX, distanceY);

      if (distance < range) {
        // Pull element towards mouse with dampening (0.35)
        setPosition({ x: distanceX * 0.35, y: distanceY * 0.35 });
      } else {
        setPosition({ x: 0, y: 0 });
      }
    };

    const handleMouseLeave = () => {
      setPosition({ x: 0, y: 0 });
    };

    element.addEventListener("mousemove", handleMouseMove);
    element.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      element.removeEventListener("mousemove", handleMouseMove);
      element.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [range]);

  const child = React.Children.only(children);
  const style = {
    ...child.props.style,
    transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
    transition: position.x === 0 && position.y === 0 
      ? "transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)" /* slow rebound spring */
      : "transform 0.15s cubic-bezier(0.25, 1, 0.5, 1)", /* quick tracking */
  };

  return React.cloneElement(child, {
    ref,
    style,
  });
}
