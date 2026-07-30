"use client";

import { motion } from "framer-motion";
import { useMotionPreference } from "./MotionProvider";

export function Reveal({
  children,
  className,
  delay = 0,
  y = 22
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}): JSX.Element {
  const { motionEnabled } = useMotionPreference();

  return (
    <motion.div
      className={className}
      initial={motionEnabled ? { opacity: 0, y } : false}
      whileInView={motionEnabled ? { opacity: 1, y: 0 } : undefined}
      viewport={{ once: true, amount: 0.16 }}
      transition={{ duration: 0.72, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
