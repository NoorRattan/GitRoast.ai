import { AdminPanel } from "./panel";

export default function AdminPage(): JSX.Element {
  return (
    <main className="page">
      <div className="shell">
        <AdminPanel />
      </div>
    </main>
  );
}
