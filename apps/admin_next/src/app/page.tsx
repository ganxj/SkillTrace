import { Dashboard } from "@/components/dashboard";
import { getDashboardData } from "@/lib/api";

export default async function Home() {
  try {
    const data = await getDashboardData();
    return <Dashboard {...data} />;
  } catch (error) {
    return (
      <main className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">AI Learning OS Admin</p>
            <h1>API Offline</h1>
          </div>
          <div className="status">local</div>
        </header>
        <section className="panel">
          <h2>Backend connection failed</h2>
          <p className="muted">
            Start the FastAPI service at http://localhost:8000/api/v1 and refresh this page.
          </p>
          <pre>{error instanceof Error ? error.message : "Unknown error"}</pre>
        </section>
      </main>
    );
  }
}

