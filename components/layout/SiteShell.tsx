"use client";

import { ArrowUpRight, Github, Menu, Moon, Sparkles, Sun, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import gsap from "gsap";
import Lenis from "lenis";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AmbientScene } from "@/components/scene/AmbientScene";
import { useMotionPreference } from "./MotionProvider";

export function SiteShell({ children }: { children: React.ReactNode }): JSX.Element {
  const pathname = usePathname();
  const { motionEnabled } = useMotionPreference();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!motionEnabled) return undefined;

    const lenis = new Lenis({
      duration: 1.05,
      smoothWheel: true,
      syncTouch: false,
      touchMultiplier: 1.1
    });
    const onTick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(onTick);
    gsap.ticker.lagSmoothing(0);

    return () => {
      gsap.ticker.remove(onTick);
      lenis.destroy();
    };
  }, [motionEnabled]);

  return (
    <div className="site-frame">
      <AmbientScene />
      <div className="grain" aria-hidden="true" />
      <header className="site-header">
        <Link className="brand-lockup" href="/" aria-label="GitRoast.ai home">
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>GitRoast<span className="brand-dot">.</span>ai</span>
        </Link>

        <nav className={`site-nav${menuOpen ? " is-open" : ""}`} aria-label="Primary navigation">
          <Link className={pathname === "/" ? "is-active" : ""} href="/">Profile audit</Link>
          <Link className={pathname === "/evaluate" ? "is-active" : ""} href="/evaluate">Project evaluator</Link>
          <a href="https://github.com/NoorRattan/GitRoast.ai" target="_blank" rel="noreferrer">
            GitHub <ArrowUpRight size={14} aria-hidden="true" />
          </a>
        </nav>

        <div className="header-tools">
          <ThemeButton />
          <MotionButton />
          <button
            className="menu-toggle"
            type="button"
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
          </button>
        </div>
      </header>

      <AnimatePresence initial={false} mode="wait">
        <motion.div
          key={pathname}
          className="route-transition"
          initial={motionEnabled ? { opacity: 0, y: 8 } : false}
          animate={{ opacity: 1, y: 0 }}
          exit={motionEnabled ? { opacity: 0, y: -8 } : undefined}
          transition={{ duration: 0.38, ease: "easeOut" }}
        >
          {children}
        </motion.div>
      </AnimatePresence>

      <footer className="site-footer">
        <span><span className="footer-pulse" aria-hidden="true" /> Evidence before ego.</span>
        <span>GitRoast.ai / 2026</span>
        <span className="footer-links">
          <a href="https://github.com/NoorRattan/GitRoast.ai" target="_blank" rel="noreferrer"><Github size={14} aria-hidden="true" /> Source</a>
          <Link href="/evaluate">Evaluate a project</Link>
        </span>
      </footer>
    </div>
  );
}

function MotionButton(): JSX.Element {
  const { motionEnabled, ready, toggleMotion } = useMotionPreference();
  const label = !ready ? "Motion preference" : motionEnabled ? "Reduce motion" : "Enable motion";

  return (
    <button
      className={`theme-button motion-button${motionEnabled ? " is-active" : ""}`}
      type="button"
      aria-label={label}
      aria-pressed={motionEnabled}
      title={label}
      onClick={toggleMotion}
    >
      <Sparkles size={16} aria-hidden="true" />
    </button>
  );
}

function ThemeButton(): JSX.Element {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    setTheme(document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark");
  }, []);

  function toggle(): void {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Storage can be unavailable in private browsing contexts.
    }
    setTheme(next);
  }

  const label = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
  return (
    <button className="theme-button" type="button" aria-label={label} aria-pressed={theme === "light"} onClick={toggle}>
      {theme === "dark" ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
    </button>
  );
}
