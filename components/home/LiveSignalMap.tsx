"use client";

import {
  Activity,
  ArrowDownRight,
  Layers3,
  Radio,
  ScanLine,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import Link from "next/link";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform
} from "framer-motion";
import { useMotionPreference } from "@/components/layout/MotionProvider";

const stars = [
  [8, 18, 0.42, 1], [17, 64, 0.2, 2], [27, 27, 0.55, 3], [36, 73, 0.26, 1],
  [46, 13, 0.35, 2], [56, 79, 0.18, 3], [63, 32, 0.5, 1], [73, 15, 0.25, 2],
  [82, 65, 0.4, 3], [91, 25, 0.2, 1], [12, 43, 0.24, 2], [77, 46, 0.25, 1],
  [69, 88, 0.18, 3], [38, 40, 0.3, 2]
] as const;

const nodes = [
  { name: "Profile", detail: "Surface", x: 22, y: 29, tone: "cyan", delay: 0 },
  { name: "Projects", detail: "Depth", x: 79, y: 34, tone: "orange", delay: 0.75 },
  { name: "Rhythm", detail: "Commit flow", x: 17, y: 72, tone: "cyan", delay: 1.4 },
  { name: "Stack", detail: "Technology", x: 84, y: 73, tone: "cyan", delay: 2.1 },
  { name: "Proof", detail: "Evidence", x: 64, y: 16, tone: "orange", delay: 2.7 }
] as const;

const statCards = [
  { label: "Surface", value: "Public profile", note: "What visitors can see", icon: ShieldCheck, tone: "cyan" },
  { label: "Signals", value: "Evidence-linked", note: "Every score has a source", icon: Radio, tone: "orange" },
  { label: "Output", value: "Actionable roast", note: "A move worth making", icon: Sparkles, tone: "violet" }
] as const;

export function LiveSignalMap(): JSX.Element {
  const { motionEnabled } = useMotionPreference();
  const prefersReducedMotion = useReducedMotion();
  const isAnimated = motionEnabled && !prefersReducedMotion;
  const pointerX = useMotionValue(0);
  const pointerY = useMotionValue(0);
  const springX = useSpring(pointerX, { stiffness: 90, damping: 19, mass: 0.55 });
  const springY = useSpring(pointerY, { stiffness: 90, damping: 19, mass: 0.55 });
  const planetX = useTransform(springX, [-1, 1], [-7, 7]);
  const planetY = useTransform(springY, [-1, 1], [6, -6]);
  const skyX = useTransform(springX, [-1, 1], [-10, 10]);
  const skyY = useTransform(springY, [-1, 1], [7, -7]);
  const starsX = useTransform(springX, [-1, 1], [-4, 4]);
  const starsY = useTransform(springY, [-1, 1], [3, -3]);

  function handlePointerMove(event: React.PointerEvent<HTMLElement>): void {
    if (!isAnimated) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    pointerX.set(((event.clientX - bounds.left) / bounds.width) * 2 - 1);
    pointerY.set(((event.clientY - bounds.top) / bounds.height) * 2 - 1);
  }

  function resetPointer(): void {
    pointerX.set(0);
    pointerY.set(0);
  }

  return (
    <motion.section
      className="signal-map-panel"
      aria-label="Live signal map"
      onPointerMove={handlePointerMove}
      onPointerLeave={resetPointer}
      initial={isAnimated ? { opacity: 0, y: 20, scale: 0.98 } : false}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.82, ease: [0.22, 1, 0.36, 1], delay: 0.12 }}
    >
      <motion.div className="signal-map-sky" style={isAnimated ? { x: skyX, y: skyY } : undefined} aria-hidden="true" />
      <motion.div className="signal-map-stars" style={isAnimated ? { x: starsX, y: starsY } : undefined} aria-hidden="true">
        {stars.map(([left, top, opacity, size], index) => (
          <i
            key={`${left}-${top}`}
            className={`signal-star signal-star-${size}`}
            style={{ left: `${left}%`, top: `${top}%`, opacity, animationDelay: `${index * -0.37}s` }}
          />
        ))}
      </motion.div>

      <div className="signal-map-header">
        <div>
          <div className="signal-map-kicker"><span className="signal-map-kicker-line" /> Realtime intelligence</div>
          <h2>LIVE SIGNAL MAP</h2>
          <p>Realtime intelligence engine monitoring public digital signals.</p>
        </div>
        <div className="signal-status" aria-label="System status: live, stable, realtime signal active">
          <span className="signal-status-light" />
          <div><strong>LIVE</strong><small>System Stable</small></div>
          <Activity size={16} aria-hidden="true" />
        </div>
      </div>

      <div className="signal-map-stage" aria-hidden="true">
        <div className="signal-map-grid" />
        <div className="signal-map-haze haze-one" />
        <div className="signal-map-haze haze-two" />

        <span className="signal-connection connection-one" />
        <span className="signal-connection connection-two" />
        <span className="signal-connection connection-three" />
        <span className="signal-packet packet-one" />
        <span className="signal-packet packet-two" />
        <span className="signal-packet packet-three" />

        <div className="signal-orbit orbit-wide" />
        <div className="signal-orbit orbit-mid" />
        <div className="signal-orbit orbit-tight" />
        <div className="signal-orbit orbit-vertical" />

        <motion.div
          className="signal-planet-wrap"
          style={isAnimated ? { rotateY: planetX, rotateX: planetY } : undefined}
        >
          <div className="signal-planet-halo" />
          <div className="signal-planet-shadow" />
          <div className="signal-planet">
            <span className="signal-planet-highlight" />
            <span className="signal-planet-scan" />
          </div>
        </motion.div>

        {nodes.map((node, index) => (
          <motion.button
            key={node.name}
            type="button"
            className={`signal-node signal-node-${node.tone}`}
            style={{ left: `${node.x}%`, top: `${node.y}%`, ["--node-delay" as string]: `${node.delay}s` }}
            aria-label={`${node.name} signal, ${node.detail}`}
            initial={isAnimated ? { opacity: 0, scale: 0.45 } : false}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: isAnimated ? 0.35 + index * 0.11 : 0, type: "spring", stiffness: 160, damping: 18 }}
            whileHover={isAnimated ? { scale: 1.32, zIndex: 4 } : undefined}
            whileTap={isAnimated ? { scale: 1.12 } : undefined}
          >
            <span className="signal-node-pulse" />
            <span className="signal-node-core" />
            <span className="signal-node-label"><strong>{node.name}</strong><small>{node.detail}</small></span>
          </motion.button>
        ))}

        <div className="signal-map-coordinates"><span>00</span><span>∞</span><span>100</span></div>
        <div className="signal-map-scan-label"><ScanLine size={13} aria-hidden="true" /> live scan</div>
      </div>

      <div className="signal-map-footer">
        <div className="signal-map-active"><span /> Realtime signal active</div>
        <span className="signal-map-footer-note">Move across the map to explore</span>
        <Link href="#method">How it works <ArrowDownRight size={15} aria-hidden="true" /></Link>
      </div>

      <motion.div
        className="signal-stat-grid"
        initial={isAnimated ? "hidden" : false}
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.09, delayChildren: 0.48 } } }}
      >
        {statCards.map(({ label, value, note, icon: Icon, tone }) => (
          <motion.div
            className={`signal-stat-card signal-stat-${tone}`}
            key={label}
            variants={{ hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="signal-stat-icon"><Icon size={16} strokeWidth={1.6} aria-hidden="true" /></div>
            <div><span>{label}</span><strong>{value}</strong><small>{note}</small></div>
            <Layers3 className="signal-stat-glyph" size={15} aria-hidden="true" />
          </motion.div>
        ))}
      </motion.div>
    </motion.section>
  );
}
