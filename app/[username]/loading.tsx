export default function Loading(): JSX.Element {
  return (
    <main className="page">
      <div className="shell grid" aria-busy="true" aria-label="Loading audit">
        <section className="panel skeleton skeleton-header" />
        <div className="grid two">
          <div className="grid">
            <section className="panel skeleton skeleton-scores" />
            <section className="panel skeleton skeleton-findings" />
            <section className="panel skeleton skeleton-roast" />
          </div>
          <aside className="grid audit-aside">
            <section className="panel skeleton skeleton-visual" />
            <section className="panel skeleton skeleton-card" />
          </aside>
        </div>
      </div>
    </main>
  );
}
