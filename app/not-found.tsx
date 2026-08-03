import Link from "next/link";
import { ArrowUpRight, FileQuestion } from "lucide-react";

export default function NotFound(): JSX.Element {
  return (
    <main className="page">
      <section className="shell panel fatal-error" role="status">
        <div
          className="admin-mark"
          style={{
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: "rgba(255, 255, 255, 0.06)",
            display: "grid",
            placeItems: "center",
            margin: "0 auto 16px"
          }}
        >
          <FileQuestion size={24} aria-hidden="true" />
        </div>
        <p className="eyebrow">404 · Page not found</p>
        <h1>This signal leads nowhere.</h1>
        <p className="muted">The profile or page URL you followed does not exist on GitRoast.ai.</p>
        <Link className="button primary" href="/">
          Return home <ArrowUpRight size={17} aria-hidden="true" />
        </Link>
      </section>
    </main>
  );
}
