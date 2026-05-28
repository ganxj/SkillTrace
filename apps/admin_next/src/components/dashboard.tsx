import { CourseImporter } from "@/components/course-importer";
import type { ContentImport, CourseSummary, DomainPack, Evidence, LearnerState, Skill } from "@/lib/api";

type DashboardProps = {
  domains: DomainPack[];
  latestDomain: DomainPack;
  skills: Skill[];
  states: LearnerState[];
  evidence: Evidence[];
  imports: ContentImport[];
  courseSummaries: CourseSummary[];
};

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function Dashboard({
  domains,
  latestDomain,
  skills,
  states,
  evidence,
  imports,
  courseSummaries
}: DashboardProps) {
  const averageMastery =
    states.length === 0 ? 0 : states.reduce((sum, item) => sum + item.mastery, 0) / states.length;
  const dueCount = states.filter((item) => {
    if (!item.review_due_at) return true;
    return new Date(item.review_due_at).getTime() <= Date.now();
  }).length;
  const latestQuestions = skills.reduce((sum, skill) => sum + skill.questions.length, 0);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI Learning OS Admin</p>
          <h1>课程管理</h1>
        </div>
        <div className="status">当前发布：{latestDomain.name}</div>
      </header>

      <section className="panel import-panel">
        <div>
          <h2>上传生成课程</h2>
          <p className="muted">
            上传 PDF / DOCX / Markdown / TXT，后端会解析文本并调用大模型生成章节、前置关系、讲解和选择题。
          </p>
        </div>
        <CourseImporter />
      </section>

      <section className="metrics" aria-label="Dashboard metrics">
        <div className="metric">
          <span>课程包</span>
          <strong>{domains.length}</strong>
        </div>
        <div className="metric">
          <span>当前章节</span>
          <strong>{skills.length}</strong>
        </div>
        <div className="metric">
          <span>当前题目</span>
          <strong>{latestQuestions}</strong>
        </div>
        <div className="metric">
          <span>到期复习</span>
          <strong>{dueCount}</strong>
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <h2>课程列表</h2>
            <p className="muted">每次上传生成一个新的课程包，App 默认展示最新发布课程。</p>
          </div>
          <span className="pill">平均掌握度 {percent(averageMastery)}</span>
        </div>
        <div className="course-table">
          <div className="table-head">
            <span>课程</span>
            <span>章节</span>
            <span>题目</span>
            <span>状态</span>
          </div>
          {courseSummaries.map((item) => (
            <details className="course-detail" key={item.domain.id} open={item.domain.id === latestDomain.id}>
              <summary className="course-row">
                <div>
                  <strong>{item.domain.name}</strong>
                  <p>{item.domain.description}</p>
                  <small>{item.domain.slug}</small>
                </div>
                <span>{item.skillCount}</span>
                <span>{item.questionCount}</span>
                <span className={item.domain.id === latestDomain.id ? "pill published" : "pill"}>
                  {item.domain.id === latestDomain.id ? "最新发布" : item.domain.version}
                </span>
              </summary>
              <div className="course-outline">
                {item.skills.map((skill, index) => (
                  <article className="chapter-preview" key={skill.id}>
                    <div className="chapter-index">{index + 1}</div>
                    <div>
                      <div className="chapter-title">
                        <strong>{skill.title}</strong>
                        <span>{skill.estimated_minutes} 分钟</span>
                        <span>{skill.questions.length} 题</span>
                      </div>
                      <p>{skill.summary}</p>
                      {skill.key_points.length > 0 && (
                        <ul>
                          {skill.key_points.slice(0, 3).map((point) => (
                            <li key={point}>{point}</li>
                          ))}
                        </ul>
                      )}
                      {skill.questions.length > 0 && (
                        <div className="question-preview">
                          <strong>题目示例：</strong>
                          <span>{skill.questions[0].prompt}</span>
                        </div>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </details>
          ))}
        </div>
      </section>

      <section className="grid">
        <Panel title="导入记录">
          <div className="stack">
            {imports.length === 0 ? (
              <p className="muted">还没有导入记录。</p>
            ) : (
              imports.map((item) => (
                <article className="row" key={item.id}>
                  <div>
                    <strong>{item.filename}</strong>
                    <p>{item.domain?.name ?? (item.error || "尚未生成课程")}</p>
                    <small>{formatDate(item.completed_at ?? item.created_at)}</small>
                    {item.error && <p className="error">{item.error}</p>}
                  </div>
                  <span className={`pill ${item.status}`}>{item.status}</span>
                </article>
              ))
            )}
          </div>
        </Panel>

        <Panel title="学习数据">
          <div className="stack">
            {states.length === 0 ? (
              <p className="muted">App 完成学习或复习后，这里会出现掌握度记录。</p>
            ) : (
              states.map((state) => (
                <article className="row state-row" key={state.id}>
                  <div>
                    <strong>{state.skill?.title ?? state.skill_id}</strong>
                    <p>{state.evidence_count} 条学习证据</p>
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
        <Panel title="当前课程章节">
          <div className="skill-list">
            {skills.map((skill) => (
              <article className="skill" key={skill.id}>
                <div className="skill-meta">
                  <span>{skill.kind}</span>
                  <span>{skill.estimated_minutes} 分钟</span>
                  <span>Lv.{skill.difficulty}</span>
                  <span>{skill.questions.length} 题</span>
                </div>
                <h2>{skill.title}</h2>
                <p>{skill.summary}</p>
                {skill.prerequisites.length > 0 && <small>前置：{skill.prerequisites.join(", ")}</small>}
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="最近答题记录">
          <div className="stack">
            {evidence.length === 0 ? (
              <p className="muted">选择题、复习和“我不会”都会记录在这里。</p>
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
