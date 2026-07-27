import Link from "next/link";

const sampleHandles = ["torvalds", "gaearon", "sindresorhus"];
const scoreSignals = [
  ["Profile", "86", "Identity, bio, social proof"],
  ["Depth", "74", "Repo quality and project range"],
  ["Cadence", "68", "Recent contribution rhythm"],
  ["Stack", "91", "Language and tooling breadth"]
];

export default function HomePage(): JSX.Element {
  return (
    <main className="page home-page">
      <div className="shell">
        <header className="topbar">
          <Link className="brand" href="/" aria-label="GitRoast.ai home">GitRoast.ai</Link>
          <nav className="topbar-actions" aria-label="Primary navigation">
            <a className="button ghost" href="https://github.com/NoorRattan/GitRoast.ai" target="_blank" rel="noreferrer">GitHub</a>
            <Link className="button" href="/admin">Admin</Link>
          </nav>
        </header>

        <section className="hero-grid" aria-labelledby="home-title">
          <div className="hero-copy">
            <p className="eyebrow">GitHub profile audit</p>
            <h1 id="home-title">Find the weak spots in a developer profile before everyone else does.</h1>
            <p className="lede">
              GitRoast turns a GitHub username into a scored audit, blunt local roast, improvement roadmap, and share card.
            </p>

            <form action="/search" className="audit-form">
              <label htmlFor="username" className="sr-only">
                GitHub username
              </label>
              <input
                id="username"
                className="input hero-input"
                name="username"
                placeholder="torvalds"
                autoComplete="off"
                pattern="[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"
                maxLength={39}
                title="Use a valid GitHub username."
                required
              />
              <button className="button primary hero-button" type="submit">Audit profile</button>
            </form>

            <div className="sample-row" aria-label="Example GitHub profiles">
              <span className="muted">Try:</span>
              {sampleHandles.map((handle) => (
                <Link key={handle} className="sample-link" href={`/${handle}`}>
                  {handle}
                </Link>
              ))}
            </div>
          </div>

          <aside className="audit-preview" aria-label="Audit preview">
            <div className="preview-header">
              <span className="preview-title">Profile scan</span>
              <span className="status-pill">Live</span>
            </div>
            <div className="terminal-lines" aria-hidden="true">
              <span>fetch github profile</span>
              <span>score repository depth</span>
              <span>generate local roast</span>
            </div>
            <div className="score-stack">
              {scoreSignals.map(([label, score, detail]) => (
                <div className="score-row" key={label}>
                  <div>
                    <strong>{label}</strong>
                    <span>{detail}</span>
                  </div>
                  <data value={score}>{score}</data>
                </div>
              ))}
            </div>
          </aside>
        </section>

        <section className="status-grid" aria-label="Deployment status">
          <div className="status-card">
            <span>Frontend</span>
            <strong>Workers.dev online</strong>
          </div>
          <div className="status-card">
            <span>Backend</span>
            <strong>Render target wired</strong>
          </div>
          <div className="status-card">
            <span>Cards</span>
            <strong>Cache-key worker ready</strong>
          </div>
        </section>
      </div>
    </main>
  );
}
