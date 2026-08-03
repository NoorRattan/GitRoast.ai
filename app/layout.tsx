import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { SITE_URL } from "@/lib/site";
import { Providers } from "./providers";
import { SiteShell } from "@/components/layout/SiteShell";
import "./globals.css";

const inter = localFont({
  src: "../workers/card/assets/fonts/Inter-Regular.woff",
  variable: "--font-inter",
  display: "swap"
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "GitRoast.ai",
    template: "%s | GitRoast.ai"
  },
  description: "Rule-based GitHub profile audits with transparent scoring, local roasts, and shareable cards.",
  applicationName: "GitRoast.ai",
  alternates: {
    canonical: SITE_URL
  },
  openGraph: {
    type: "website",
    siteName: "GitRoast.ai",
    title: "GitRoast.ai",
    description: "Transparent GitHub profile scoring, a local roast, and a practical improvement roadmap.",
    url: SITE_URL
  }
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#101111" },
    { media: "(prefers-color-scheme: light)", color: "#f0ece3" }
  ],
  colorScheme: "dark light"
};

// Inline script evaluated synchronously before first paint to prevent
// flash of wrong theme. Must not reference external variables.
const noFlashScript = `(function(){try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t);}else{var q=window.matchMedia('(prefers-color-scheme: dark)');document.documentElement.setAttribute('data-theme',q.matches?'dark':'light');}var m=localStorage.getItem('motion-override');if(m==='on'||m==='off'){document.documentElement.setAttribute('data-motion',m);}else if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){document.documentElement.setAttribute('data-motion','off');}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <html className={inter.variable} lang="en" suppressHydrationWarning>
      <head>
        {/* Synchronous theme bootstrap — must run before body renders */}
        <script dangerouslySetInnerHTML={{ __html: noFlashScript }} />
      </head>
      <body>
        <Providers>
          <SiteShell>{children}</SiteShell>
        </Providers>
      </body>
    </html>
  );
}
