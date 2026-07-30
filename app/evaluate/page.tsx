import { ProjectEvaluationClient } from "@/components/evaluation/ProjectEvaluationClient";

export default function EvaluatePage(): JSX.Element {
  return (
    <main className="page">
      <div className="shell">
        <ProjectEvaluationClient />
      </div>
    </main>
  );
}
