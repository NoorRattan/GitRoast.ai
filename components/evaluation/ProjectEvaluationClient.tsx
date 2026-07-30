"use client";

import { SearchCode } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import type { ProjectCategoryEvaluation, ProjectEvaluationResult } from "@/lib/api-client";
import { ApiError, requestProjectEvaluation } from "@/lib/api-client";

const categoryLabels: Record<string, string> = {
  problem_statement_alignment: "Problem alignment",
  code_quality: "Code quality",
  security: "Security",
  testing_reliability: "Testing & reliability",
  efficiency: "Efficiency",
  documentation_accessibility: "Documentation & accessibility"
};

const loadingStages = [
  "Reading repository structure",
  "Selecting key files",
  "Running static checks",
  "Scoring rubric",
  "Cross-checking evidence"
];

export function ProjectEvaluationClient(): JSX.Element {
  const [repoUrl, setRepoUrl] = useState("");
  const [problemStatement, setProblemStatement] = useState("");
  const [result, setResult] = useState<ProjectEvaluationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const orderedCategories = useMemo(() => (
    result ? Object.entries(result.categories).sort(([left], [right]) => categoryOrder(left) - categoryOrder(right)) : []
  ), [result]);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      setResult(await requestProjectEvaluation(repoUrl.trim(), problemStatement.trim()));
    } catch (caught) {
      setError(projectEvaluationError(caught));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid evaluation-grid">
      <section className="double-bezel-shell">
        <div className="double-bezel-core evaluation-form-panel">
          <p className="eyebrow">Deep project evaluator</p>
          <h1 className="evaluation-title">Score a repo against the problem it claims to solve.</h1>
          <form className="evaluation-form" onSubmit={(event) => void onSubmit(event)}>
            <label>
              <span>GitHub repository URL</span>
              <input
                className="input"
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                placeholder="https://github.com/owner/repo"
                inputMode="url"
                required
              />
            </label>
            <label>
              <span>Problem statement</span>
              <textarea
                className="input evaluation-textarea"
                value={problemStatement}
                onChange={(event) => setProblemStatement(event.target.value)}
                minLength={20}
                maxLength={4000}
                required
              />
            </label>
            <button className="button primary active-tactile" type="submit" disabled={isSubmitting}>
              <SearchCode size={18} aria-hidden="true" />
              {isSubmitting ? "Evaluating" : "Evaluate project"}
            </button>
          </form>
          {error ? <p className="search-error" role="alert">{error}</p> : null}
        </div>
      </section>

      <section className="double-bezel-shell" aria-live="polite">
        <div className="double-bezel-core evaluation-status-panel">
          {isSubmitting ? (
            <ol className="evaluation-stage-list">
              {loadingStages.map((stage, index) => (
                <li key={stage} className={index === 0 ? "active" : ""}>{stage}</li>
              ))}
            </ol>
          ) : result ? (
            <EvaluationSummary result={result} orderedCategories={orderedCategories} />
          ) : (
            <div className="evaluation-empty">
              <strong>Strict by default</strong>
              <span>Scores require file-level evidence, non-applicable axes are excluded, and 80+ categories are capped unless citations justify them.</span>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function EvaluationSummary({
  result,
  orderedCategories
}: {
  result: ProjectEvaluationResult;
  orderedCategories: Array<[string, ProjectCategoryEvaluation]>;
}): JSX.Element {
  const flags = Object.entries(result.flags).filter(([, enabled]) => enabled);
  return (
    <div className="evaluation-result">
      <div className="evaluation-scoreband">
        <data value={result.overallScore}>{result.overallScore}</data>
        <div>
          <strong>{result.gradeLabel}</strong>
          <span>{result.projectType.replace(/_/g, " ")}</span>
        </div>
      </div>
      <p className="muted flush">{result.calibrationNote}</p>
      {flags.length ? (
        <div className="evaluation-flags" aria-label="Evaluator flags">
          {flags.map(([flag]) => <span key={flag}>{flag.replace(/[A-Z]/g, (letter) => ` ${letter.toLowerCase()}`)}</span>)}
        </div>
      ) : null}
      <div className="evaluation-categories">
        {orderedCategories.map(([key, category]) => (
          <details className="evaluation-category" key={key}>
            <summary>
              <span>{categoryLabels[key] ?? key}</span>
              <data value={category.score}>{category.score}</data>
            </summary>
            <p>{category.bandJustification}</p>
            <ul>
              {category.evidence.map((item) => (
                <li key={`${item.file}-${item.detail}`}>
                  <code>{item.file}</code>
                  <span>{item.detail}</span>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </div>
      {result.excludedCategories.length ? (
        <p className="muted flush">Excluded: {result.excludedCategories.join(", ")}.</p>
      ) : null}
    </div>
  );
}

function projectEvaluationError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "The project could not be evaluated right now.";
  }
  if (error.status === 404) {
    return "That public GitHub repository could not be found.";
  }
  if (error.status === 422) {
    return "Enter a public GitHub repository URL and a problem statement of at least 20 characters.";
  }
  if (error.status === 429) {
    return "Too many project evaluations were requested from this connection. Try again later.";
  }
  if (error.status === 503) {
    return "GitHub is temporarily unavailable. Retry in a moment.";
  }
  return error.message || "The project could not be evaluated right now.";
}

function categoryOrder(key: string): number {
  return [
    "problem_statement_alignment",
    "code_quality",
    "security",
    "testing_reliability",
    "efficiency",
    "documentation_accessibility"
  ].indexOf(key);
}
