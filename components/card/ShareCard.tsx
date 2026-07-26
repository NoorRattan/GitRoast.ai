import { buildCardImageUrl } from "@/lib/api-client";

type ShareCardProps = {
  username: string;
  schemaVersion: number;
};

/** Renders the expected Session 5 card-worker image URL, including backend schema_version. */
export function ShareCard({ username, schemaVersion }: ShareCardProps): JSX.Element {
  const imageUrl = buildCardImageUrl(username, schemaVersion);
  return (
    <section className="panel" style={{ padding: 16 }}>
      <img
        src={imageUrl}
        alt={`${username} GitRoast share card`}
        width={1200}
        height={630}
        style={{ width: "100%", height: "auto", borderRadius: 8, border: "1px solid var(--line)" }}
      />
      <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
        <a className="button" href={imageUrl} target="_blank" rel="noreferrer">Open</a>
        <a className="button" href={`https://github.com/${encodeURIComponent(username)}`} target="_blank" rel="noreferrer">GitHub</a>
      </div>
    </section>
  );
}
