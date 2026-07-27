import type { Metadata } from "next";
import { AuditClient } from "@/components/audit/AuditClient";
import { buildCardImageUrl, fetchCachedAudit } from "@/lib/api-client";

type UsernamePageProps = {
  params: Promise<{
    username: string;
  }>;
};

export async function generateMetadata({ params }: UsernamePageProps): Promise<Metadata> {
  const { username: rawUsername } = await params;
  const username = decodeURIComponent(rawUsername);
  const audit = await safeFetchCachedAudit(username);
  const imageUrl = audit ? buildCardImageUrl(username, audit.schemaVersion) : "https://gitroast-card-preview.jnoorrattan.workers.dev/card/generic.png";
  return {
    title: audit ? `${username} GitRoast` : `${username} GitRoast pending`,
    description: audit ? audit.roastText.slice(0, 150) : "GitRoast audit result shell.",
    openGraph: {
      title: audit ? `${username} GitRoast` : `${username} GitRoast pending`,
      description: audit ? audit.roastText.slice(0, 150) : "GitRoast audit result shell.",
      images: [
        {
          url: imageUrl,
          width: 1200,
          height: 630,
          alt: `${username} GitRoast card`
        }
      ]
    }
  };
}

export default async function UsernamePage({ params }: UsernamePageProps): Promise<JSX.Element> {
  const { username: rawUsername } = await params;
  const username = decodeURIComponent(rawUsername);
  const audit = await safeFetchCachedAudit(username);
  // Accepted v1 trade-off: a brand-new profile gets generic OG metadata because the server path only performs the fast GET cache read; the browser POST fills the result afterward.
  return (
    <main className="page">
      <div className="shell">
        <AuditClient username={username} initialAudit={audit} />
      </div>
    </main>
  );
}

async function safeFetchCachedAudit(username: string) {
  try {
    return await fetchCachedAudit(username);
  } catch {
    return null;
  }
}
