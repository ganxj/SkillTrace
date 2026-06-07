import { Dashboard } from "@/components/dashboard";
import { getDashboardData } from "@/lib/api";

export const dynamic = "force-dynamic";

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
            <h1>后端未连接</h1>
          </div>
          <div className="status">local</div>
        </header>
        <section className="panel">
          <h2>无法连接后端服务</h2>
          <p className="muted">
            请先启动 FastAPI 服务：http://192.168.1.192:8001/api/v1，然后刷新页面。
          </p>
          <pre>{error instanceof Error ? error.message : "Unknown error"}</pre>
        </section>
      </main>
    );
  }
}
