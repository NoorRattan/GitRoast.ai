import Link from "next/link";

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
        </header>

        <section className="hero-grid" aria-labelledby="home-title">
          <div className="hero-copy">
            <p className="eyebrow">GitHub profile audit</p>
            <h1 id="home-title">Find the weak spots in a developer profile before everyone else does.</h1>
            <p className="lede">
              GitRoast turns a GitHub profile link into a scored audit, blunt local roast, improvement roadmap, and share card.
            </p>

            <form action="/search" className="audit-form">
              <label htmlFor="username" className="sr-only">
                GitHub profile link
              </label>
              <input
                id="username"
                className="input hero-input"
                name="username"
                placeholder="https://github.com/your-handle"
                autoComplete="off"
                inputMode="url"
                title="Paste a GitHub profile link, or type a GitHub username."
                required
              />
              <button className="button primary hero-button" type="submit">Audit profile</button>
            </form>
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
