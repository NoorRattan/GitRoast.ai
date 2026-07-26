import Link from "next/link";

export default function HomePage(): JSX.Element {
  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div className="brand">GitRoast.ai</div>
          <Link className="button" href="/admin">Admin</Link>
        </header>
        <section className="panel" style={{ padding: 24, maxWidth: 680 }}>
          <h1>Audit a GitHub profile</h1>
          <form action="/search" style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label htmlFor="username" className="muted" style={{ position: "absolute", left: -10000 }}>
              GitHub username
            </label>
            <input id="username" className="input" name="username" placeholder="torvalds" autoComplete="off" pattern="[A-Za-z0-9-]+" required />
            <button className="button primary" type="submit">Audit</button>
          </form>
        </section>
      </div>
    </main>
  );
}
