import type { Metadata } from "next";
import { AdminPanel } from "./panel";

export const metadata: Metadata = {
  title: "Review queue | GitRoast.ai",
  robots: {
    index: false,
    follow: false
  }
};

export default function AdminPage(): JSX.Element {
  return (
    <main className="page">
      <div className="shell">
        <AdminPanel />
      </div>
    </main>
  );
}
