import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { SITE_URL } from "@/lib/site";
import { Providers } from "./providers";
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
  openGraph: {
    type: "website",
    siteName: "GitRoast.ai",
    title: "GitRoast.ai",
    description: "Transparent GitHub profile scoring, a local roast, and a practical improvement roadmap."
  }
};

export const viewport: Viewport = {
  themeColor: "#101111",
  colorScheme: "dark"
};

export default function RootLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <html className={inter.variable} lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
