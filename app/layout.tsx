import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { SITE_URL } from "@/lib/site";
import { Providers } from "./providers";
import { ThemeToggle } from "@/components/ThemeToggle";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap"
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
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
  openGraph: {
    type: "website",
    siteName: "GitRoast.ai",
    title: "GitRoast.ai",
    description: "Transparent GitHub profile scoring, a local roast, and a practical improvement roadmap."
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
const noFlashScript = `(function(){try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t);return;}var q=window.matchMedia('(prefers-color-scheme: dark)');document.documentElement.setAttribute('data-theme',q.matches?'dark':'light');}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <html className={`${geistSans.variable} ${geistMono.variable}`} lang="en">
      <head>
        {/* Synchronous theme bootstrap — must run before body renders */}
        <script dangerouslySetInnerHTML={{ __html: noFlashScript }} />
      </head>
      <body>
        <Providers>{children}</Providers>
        <ThemeToggle />
      </body>
    </html>
  );
}
