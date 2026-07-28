"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type Theme = "dark" | "light";


/** Floating theme toggle button — reads and writes data-theme on <html>. */
export function ThemeToggle(): JSX.Element {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    // Sync with whatever the no-flash inline script already set.
    const attr = document.documentElement.getAttribute("data-theme");
    setTheme(attr === "light" ? "light" : "dark");
  }, []);

  function toggle(): void {
    const next: Theme = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      // localStorage may be blocked in some private-browsing contexts.
    }
    setTheme(next);
  }

  const label = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";

  return (
    <button
      type="button"
      className="theme-toggle"
      aria-label={label}
      aria-pressed={theme === "light"}
      title={label}
      onClick={toggle}
    >
      {theme === "dark" ? (
        <Sun aria-hidden="true" size={20} strokeWidth={1.8} />
      ) : (
        <Moon aria-hidden="true" size={20} strokeWidth={1.8} />
      )}
    </button>
  );
}
