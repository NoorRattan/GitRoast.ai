import Link from "next/link";
import { ProjectEvaluationClient } from "@/components/evaluation/ProjectEvaluationClient";

export default function EvaluatePage(): JSX.Element {
  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <Link className="brand" href="/" aria-label="GitRoast.ai home">GitRoast.ai</Link>
          <nav className="topbar-actions" aria-label="Primary navigation">
            <Link className="button ghost" href="/">Profile audit</Link>
            <a className="button ghost" href="https://github.com/NoorRattan/GitRoast.ai" target="_blank" rel="noreferrer">GitHub</a>
          </nav>
        </header>
        <ProjectEvaluationClient />
      </div>
    </main>
  );
}
