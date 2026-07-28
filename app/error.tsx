"use client";

import { RefreshCw } from "lucide-react";
import { useEffect } from "react";
import { captureFrontendError } from "@/lib/monitoring";

export default function GlobalError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  useEffect(() => {
    void captureFrontendError(error);
  }, [error]);

  return (
    <main className="page">
      <section className="shell panel fatal-error" role="alert">
        <p className="eyebrow">Render failure</p>
        <h1>This page hit an unexpected error.</h1>
        <p className="muted">The audit data is safe. Retry the current view.</p>
        <button className="button primary" type="button" onClick={reset}>
          <RefreshCw aria-hidden="true" size={17} /> Retry
        </button>
      </section>
    </main>
  );
}
