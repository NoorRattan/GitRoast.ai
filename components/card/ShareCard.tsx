"use client";

import { ArrowUpRight, Check, Copy, ExternalLink, Github, Share2 } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { buildCardImageUrl } from "@/lib/api-client";

type ShareCardProps = {
  username: string;
  schemaVersion: number;
};

/** Renders the expected Session 5 card-worker image URL, including backend schema_version. */
export function ShareCard({ username, schemaVersion }: ShareCardProps): JSX.Element {
  const imageUrl = buildCardImageUrl(username, schemaVersion);
  const [copied, setCopied] = useState(false);
  const siteBaseUrl = (
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://gitroast-ai-frontend.jnoorrattan.workers.dev"
  ).replace(/\/$/, "");
  const shareUrl = `${siteBaseUrl}/${encodeURIComponent(username)}`;
  const shareText = `${username}'s GitRoast profile audit`;

  async function share(): Promise<void> {
    if (navigator.share) {
      await navigator.share({ title: shareText, text: shareText, url: shareUrl });
      return;
    }
    await copyLink();
  }

  async function copyLink(): Promise<void> {
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <section className="share-card">
      <div className="share-card-heading"><span className="section-kicker">The artifact</span><ArrowUpRight size={17} aria-hidden="true" /></div>
      <div className="share-image-frame"><Image src={imageUrl} alt={`${username} GitRoast share card`} width={1200} height={630} unoptimized className="share-card-image" /></div>
      <p className="share-card-copy">Keep the read. Share the receipt. Come back when the signal changes.</p>
      <div className="share-actions">
        <button className="button primary" type="button" onClick={() => void share()}>
          <Share2 aria-hidden="true" size={17} /> Share
        </button>
        <button className="button" type="button" onClick={() => void copyLink()}>
          {copied ? <Check aria-hidden="true" size={17} /> : <Copy aria-hidden="true" size={17} />}
          {copied ? "Copied" : "Copy link"}
        </button>
        <a className="button icon-button" href={imageUrl} target="_blank" rel="noreferrer" aria-label="Open card image" title="Open card image">
          <ExternalLink aria-hidden="true" size={18} />
        </a>
        <a className="button icon-button" href={`https://github.com/${encodeURIComponent(username)}`} target="_blank" rel="noreferrer" aria-label="Open GitHub profile" title="Open GitHub profile">
          <Github aria-hidden="true" size={18} />
        </a>
        <a
          className="button"
          href={`https://x.com/intent/post?text=${encodeURIComponent(`${shareText} ${shareUrl}`)}`}
          target="_blank"
          rel="noreferrer"
        >
          Post to X
        </a>
      </div>
    </section>
  );
}
