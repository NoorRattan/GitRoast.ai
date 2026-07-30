"use client";

import { ArrowUpRight, Check, FileSearch, SearchCode, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
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
  const [activeStage, setActiveStage] = useState(0);
  const orderedCategories = useMemo(() => (
    result ? Object.entries(result.categories).sort(([left], [right]) => categoryOrder(left) - categoryOrder(right)) : []
  ), [result]);

  useEffect(() => {
    if (!isSubmitting) return undefined;
    const timer = window.setInterval(() => setActiveStage((stage) => Math.min(stage + 1, loadingStages.length - 1)), 700);
    return () => window.clearInterval(timer);
  }, [isSubmitting]);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setIsSubmitting(true);
    setActiveStage(0);
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
    <div className="evaluation-layout">
      <section className="evaluation-form-panel" aria-labelledby="evaluation-title">
        <div className="evaluation-heading-row"><span className="section-kicker">Deep project evaluator</span><span className="route-index">02 / 03</span></div>
        <h1 id="evaluation-title">Score a repo against the problem it claims to solve.</h1>
        <p className="evaluation-lede">Give the evaluator the claim. It will inspect the public repository, find the proof, and show you where the story breaks.</p>
        <form className="evaluation-form" onSubmit={(event) => void onSubmit(event)}>
          <label>
            <span>Repository URL</span>
            <div className="input-command"><FileSearch size={17} aria-hidden="true" /><input value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} placeholder="https://github.com/owner/repo" inputMode="url" required /></div>
          </label>
          <label>
            <span>Problem statement</span>
            <textarea value={problemStatement} onChange={(event) => setProblemStatement(event.target.value)} minLength={20} maxLength={4000} placeholder="What problem does this project claim to solve?" required />
          </label>
          <div className="form-footer"><span>Public repository · evidence-linked output</span><button className="button primary" type="submit" disabled={isSubmitting}><SearchCode size={17} aria-hidden="true" />{isSubmitting ? "Reading project" : "Evaluate project"}<ArrowUpRight size={16} aria-hidden="true" /></button></div>
        </form>
        {error ? <p className="search-error" role="alert">{error}</p> : null}
      </section>

      <section className="evaluation-status-panel" aria-live="polite">
        {isSubmitting ? (
          <div className="evaluation-loading-state">
            <div className="loading-orbit" aria-hidden="true"><span /><span /><span /></div>
            <p className="section-kicker">Evidence pass in progress</p>
            <h2>Reading the repo beneath the README.</h2>
            <ol className="evaluation-stage-list">
              {loadingStages.map((stage, index) => <li key={stage} className={index <= activeStage ? "is-active" : ""}><span>{index < activeStage ? <Check size={13} aria-hidden="true" /> : index + 1}</span>{stage}</li>)}
            </ol>
          </div>
        ) : result ? (
          <EvaluationSummary result={result} orderedCategories={orderedCategories} />
        ) : (
          <div className="evaluation-empty">
            <div className="empty-signal"><ShieldCheck size={20} aria-hidden="true" /></div>
            <p className="section-kicker">Strict by default</p>
            <h2>Claims need receipts.</h2>
            <p>Scores require file-level evidence, non-applicable axes are excluded, and 80+ categories are capped unless citations justify them.</p>
            <div className="empty-line"><span /> Ready when you are</div>
          </div>
        )}
      </section>
    </div>
  );
}

function EvaluationSummary({ result, orderedCategories }: { result: ProjectEvaluationResult; orderedCategories: Array<[string, ProjectCategoryEvaluation]> }): JSX.Element {
  const flags = Object.entries(result.flags).filter(([, enabled]) => enabled);
  return (
    <div className="evaluation-result">
      <div className="evaluation-result-head"><div className="score-ring" style={{ "--score": `${result.overallScore * 3.6}deg` } as React.CSSProperties}><span>{result.overallScore}</span><small>/ 100</small></div><div><p className="section-kicker">Evaluation complete</p><h2>{result.gradeLabel}</h2><p className="project-type">{result.projectType.replace(/_/g, " ")}</p></div></div>
      <p className="calibration-note">{result.calibrationNote}</p>
      {flags.length ? <div className="evaluation-flags" aria-label="Evaluator flags">{flags.map(([flag]) => <span key={flag}>{flag.replace(/[A-Z]/g, (letter) => ` ${letter.toLowerCase()}`)}</span>)}</div> : null}
      <div className="evaluation-categories">
        {orderedCategories.map(([key, category], index) => (
          <details className="evaluation-category" key={key} open={index === 0}>
            <summary><span className="category-number">0{index + 1}</span><span className="category-name">{categoryLabels[key] ?? key}</span><span className="category-score">{category.score}</span><ArrowUpRight size={16} aria-hidden="true" /></summary>
            <div className="category-detail"><p>{category.bandJustification}</p><ul>{category.evidence.map((item) => <li key={`${item.file}-${item.detail}`}><code>{item.file}</code><span>{item.detail}</span></li>)}</ul></div>
          </details>
        ))}
      </div>
      {result.excludedCategories.length ? <p className="excluded-note">Excluded from this pass: {result.excludedCategories.join(", ")}.</p> : null}
    </div>
  );
}

function projectEvaluationError(error: unknown): string {
  if (!(error instanceof ApiError)) return "The project could not be evaluated right now.";
  if (error.status === 404) return "That public GitHub repository could not be found.";
  if (error.status === 422) return "Enter a public GitHub repository URL and a problem statement of at least 20 characters.";
  if (error.status === 429) return "Too many project evaluations were requested from this connection. Try again later.";
  if (error.status === 503) return "GitHub is temporarily unavailable. Retry in a moment.";
  return error.message || "The project could not be evaluated right now.";
}

function categoryOrder(key: string): number {
  return ["problem_statement_alignment", "code_quality", "security", "testing_reliability", "efficiency", "documentation_accessibility"].indexOf(key);
}
