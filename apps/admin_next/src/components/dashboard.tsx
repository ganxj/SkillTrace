import type { DomainPack, Evidence, LearnerState, Skill } from "@/lib/api";

type DashboardProps = {
  domains: DomainPack[];
  skills: Skill[];
  states: LearnerState[];
  evidence: Evidence[];
};

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function Dashboard({ domains, skills, states, evidence }: DashboardProps) {
  const averageMastery =
    states.length === 0
      ? 0
      : states.reduce((sum, item) => sum + item.mastery, 0) / states.length;
  const dueCount = states.filter((item) => {
    if (!item.review_due_at) return true;
    return new Date(item.review_due_at).getTime() <= Date.now();
  }).length;

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI Learning OS Admin</p>
          <h1>Learning State Console</h1>
        </div>
        <div className="status">demo-user</div>
      </header>

      <section className="metrics" aria-label="Dashboard metrics">
        <div className="metric">
          <span>Domain Packs</span>
          <strong>{domains.length}</strong>
        </div>
        <div className="metric">
          <span>Quant Skills</span>
          <strong>{skills.length}</strong>
        </div>
        <div className="metric">
          <span>Average Mastery</span>
          <strong>{percent(averageMastery)}</strong>
        </div>
        <div className="metric">
          <span>Due Reviews</span>
          <strong>{dueCount}</strong>
        </div>
      </section>

      <section className="grid">
        <Panel title="Domain Packs">
          <div className="stack">
            {domains.map((domain) => (
              <article className="row" key={domain.id}>
                <div>
                  <strong>{domain.name}</strong>
                  <p>{domain.description}</p>
                </div>
                <span className="pill">{domain.version}</span>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Learner State">
          <div className="stack">
            {states.length === 0 ? (
              <p className="muted">No evidence yet. Complete a mobile learning session first.</p>
            ) : (
              states.map((state) => (
                <article className="row state-row" key={state.id}>
                  <div>
                    <strong>{state.skill?.title ?? state.skill_id}</strong>
                    <p>{state.evidence_count} evidence records</p>
                  </div>
                  <div className="bars">
                    <Progress label="M" value={state.mastery} />
                    <Progress label="C" value={state.confidence} />
                  </div>
                </article>
              ))
            )}
          </div>
        </Panel>
      </section>

      <section className="grid wide">
        <Panel title="Quant Skill Graph">
          <div className="skill-list">
            {skills.map((skill) => (
              <article className="skill" key={skill.id}>
                <div className="skill-meta">
                  <span>{skill.kind}</span>
                  <span>{skill.estimated_minutes} min</span>
                  <span>Lv.{skill.difficulty}</span>
                </div>
                <h2>{skill.title}</h2>
                <p>{skill.summary}</p>
                {skill.prerequisites.length > 0 && (
                  <small>Prerequisites: {skill.prerequisites.join(", ")}</small>
                )}
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Recent Evidence">
          <div className="stack">
            {evidence.length === 0 ? (
              <p className="muted">Evidence will appear after quiz, explain, review, or transfer tasks.</p>
            ) : (
              evidence.map((item) => (
                <article className="row" key={item.id}>
                  <div>
                    <strong>{item.evidence_type}</strong>
                    <p>{item.feedback || item.response || item.prompt}</p>
                  </div>
                  <span className="score">{percent(item.score)}</span>
                </article>
              ))
            )}
          </div>
        </Panel>
      </section>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Progress({ label, value }: { label: string; value: number }) {
  return (
    <div className="progress">
      <span>{label}</span>
      <div aria-label={`${label} ${percent(value)}`}>
        <i style={{ width: percent(value) }} />
      </div>
    </div>
  );
}

