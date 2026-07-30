import { ArrowDownRight, ArrowUpRight, FileCheck2, Fingerprint, Share2 } from "lucide-react";
import Link from "next/link";
import { Reveal } from "@/components/layout/Reveal";

const methodItems = [
  { icon: Fingerprint, index: "01", title: "Read the surface", body: "Profile shape, pinned work, languages, commits, licenses, and the signals visitors actually see." },
  { icon: FileCheck2, index: "02", title: "Show the proof", body: "Every score stays attached to observable evidence. No mystery model score. No vibes disguised as data." },
  { icon: Share2, index: "03", title: "Leave with a move", body: "A blunt roast, a practical four-week roadmap, and a shareable artifact you can keep improving." }
];

export default async function HomePage({
  searchParams
}: {
  searchParams: Promise<{ error?: string }>;
}): Promise<JSX.Element> {
  const { error } = await searchParams;

  return (
    <main className="page home-page">
      <div className="shell">
        <section className="home-hero" aria-labelledby="home-title">
          <Reveal className="hero-column">
            <p className="eyebrow"><span className="eyebrow-dot" /> GitHub profile intelligence</p>
            <h1 id="home-title">Turn your GitHub into <em>evidence.</em></h1>
            <p className="hero-lede">A transparent audit for the work behind the profile. Find what is strong, what is missing, and the next move worth making.</p>
            <form action="/search" className="audit-form" id="profile-search">
              <label htmlFor="username" className="sr-only">GitHub profile link</label>
              <div className="input-command">
                <span className="input-prefix" aria-hidden="true">github.com/</span>
                <input id="username" name="username" placeholder="your-handle" autoComplete="off" inputMode="url" title="Paste a GitHub profile link, or type a GitHub username." required />
              </div>
              <button className="button primary hero-button" type="submit">Audit profile <ArrowUpRight size={17} aria-hidden="true" /></button>
            </form>
            {error === "invalid-profile" ? (
              <p className="search-error" role="alert">Enter a GitHub username or a profile link such as https://github.com/your-handle.</p>
            ) : null}
            <div className="hero-meta"><span>Public data only</span><span>Rule-based scoring</span><span>No account required</span></div>
          </Reveal>

          <Reveal className="scan-console-wrap" delay={0.12}>
            <div className="scan-console" aria-label="Live profile scan visualization">
              <div className="scan-console-top"><span className="section-kicker">Live signal map</span><span className="live-chip"><i /> Ready</span></div>
              <div className="scan-orbit" aria-hidden="true">
                <div className="orbit-ring orbit-ring-one" />
                <div className="orbit-ring orbit-ring-two" />
                <div className="orbit-core"><span /><span /><span /></div>
                <div className="orbit-node node-one" /><div className="orbit-node node-two" /><div className="orbit-node node-three" />
              </div>
              <div className="scan-readout">
                <div><span>Surface</span><strong>Public profile</strong></div>
                <div><span>Signals</span><strong>Evidence-linked</strong></div>
                <div><span>Output</span><strong>Actionable roast</strong></div>
              </div>
              <div className="scan-console-bottom"><span><i className="status-dot" /> Waiting for a handle</span><Link href="#method">How it works <ArrowDownRight size={14} aria-hidden="true" /></Link></div>
            </div>
          </Reveal>
        </section>

        <Reveal className="proof-strip" delay={0.08}>
          <span className="proof-label">A better profile starts with a sharper read</span>
          <div className="proof-items"><span>Profile shape</span><i /> <span>Project depth</span><i /> <span>Commit rhythm</span><i /> <span>Stack signal</span></div>
        </Reveal>

        <section className="method-section" id="method" aria-labelledby="method-title">
          <Reveal className="section-intro">
            <p className="eyebrow">The intelligence layer</p>
            <h2 id="method-title">Less dashboard. More <em>diagnosis.</em></h2>
            <p>GitRoast keeps the read legible. You see the surface, the proof behind it, and the sequence that turns a weak signal into visible progress.</p>
          </Reveal>
          <div className="method-list">
            {methodItems.map(({ icon: Icon, index, title, body }, itemIndex) => (
              <Reveal className="method-item" key={index} delay={itemIndex * 0.08}>
                <span className="method-index">{index}</span>
                <Icon size={22} strokeWidth={1.4} aria-hidden="true" />
                <div><h3>{title}</h3><p>{body}</p></div>
                <ArrowUpRight className="method-arrow" size={18} aria-hidden="true" />
              </Reveal>
            ))}
          </div>
        </section>

        <Reveal className="home-cta" delay={0.06}>
          <div><p className="eyebrow">Start with the uncomfortable version</p><h2>Your profile is already telling a story.</h2></div>
          <Link className="button outline-button" href="#profile-search">Read it properly <ArrowUpRight size={17} aria-hidden="true" /></Link>
        </Reveal>
      </div>
    </main>
  );
}
