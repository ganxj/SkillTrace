"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, apiErrorMessage, readApiJson } from "@/lib/api";
import type { ContentImport, CourseSummary, DomainPack, Evidence, LearnerState, Skill } from "@/lib/api";

type DashboardProps = {
  domains: DomainPack[];
  latestDomain: DomainPack | null;
  skills: Skill[];
  states: LearnerState[];
  evidence: Evidence[];
  imports: ContentImport[];
  courseSummaries: CourseSummary[];
};

type AdminSection = "overview" | "courses" | "imports" | "learning";

const activeImportStatuses = new Set(["extracting", "queued", "generating", "pause_requested", "publishing"]);
const pausableImportStatuses = new Set(["extracting", "queued", "generating", "publishing"]);
const resumableImportStatuses = new Set(["pause_requested", "paused", "failed"]);

const navItems: Array<{ id: AdminSection; label: string; description: string }> = [
  { id: "overview", label: "概览", description: "当前课程与系统状态" },
  { id: "courses", label: "课程管理", description: "课程列表、新增和生成" },
  { id: "imports", label: "导入记录", description: "生成进度和失败信息" },
  { id: "learning", label: "学习数据", description: "掌握度与答题记录" }
];

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

export function Dashboard(props: DashboardProps) {
  const [section, setSection] = useState<AdminSection>("overview");
  const { domains, latestDomain } = props;

  return (
    <main className="admin-layout">
      <aside className="admin-sidebar">
        <div className="brand">
          <p className="eyebrow">AI Learning OS</p>
          <h1>管理后台</h1>
        </div>
        <nav className="admin-nav" aria-label="Admin navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={section === item.id ? "active" : ""}
              onClick={() => setSection(item.id)}
            >
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </button>
          ))}
        </nav>
      </aside>

      <section className="admin-main">
        <header className="admin-topbar">
          <div>
            <p className="eyebrow">{navItems.find((item) => item.id === section)?.label}</p>
            <h2>{sectionTitle(section)}</h2>
          </div>
          <div className="status">{latestDomain ? `当前发布：${latestDomain.name}` : "暂无课程"}</div>
        </header>

        {section === "overview" && <OverviewPanel {...props} />}
        {section === "courses" && <CoursesPanel {...props} />}
        {section === "imports" && <ImportsPanel imports={props.imports} />}
        {section === "learning" && <LearningPanel states={props.states} evidence={props.evidence} />}
      </section>
    </main>
  );
}

function sectionTitle(section: AdminSection) {
  return {
    overview: "系统概览",
    courses: "课程管理",
    imports: "导入记录",
    learning: "学习数据"
  }[section];
}

function OverviewPanel({ domains, latestDomain, skills, states, imports }: DashboardProps) {
  const averageMastery =
    states.length === 0 ? 0 : states.reduce((sum, item) => sum + item.mastery, 0) / states.length;
  const latestQuestions = skills.reduce((sum, skill) => sum + skill.questions.length, 0);
  const runningImports = imports.filter((item) => activeImportStatuses.has(item.status)).length;

  return (
    <div className="admin-content">
      <section className="metrics" aria-label="Dashboard metrics">
        <Metric label="课程数量" value={domains.length} />
        <Metric label="当前章节" value={skills.length} />
        <Metric label="当前题目" value={latestQuestions} />
        <Metric label="生成任务" value={runningImports} />
      </section>

      <section className="grid">
        <Panel title="当前发布课程">
          {latestDomain ? (
            <div className="summary-block">
              <strong>{latestDomain.name}</strong>
              <p>{latestDomain.description || latestDomain.slug}</p>
              <div className="summary-meta">
                <span>{skills.length} 个章节</span>
                <span>{latestQuestions} 道题</span>
                <span>平均掌握度 {percent(averageMastery)}</span>
              </div>
            </div>
          ) : (
            <EmptyState title="暂无课程" text="先进入“内容生成”新增课程，再上传文件生成章节和题目。" />
          )}
        </Panel>

        <Panel title="最近生成">
          <ImportList imports={imports.slice(0, 5)} />
        </Panel>
      </section>
    </div>
  );
}

type ImportResult = {
  import_record: ContentImport;
  domain: { id: string; name: string; slug: string } | null;
  skill_count: number;
  question_count: number;
};

function CoursesPanel({ courseSummaries, latestDomain, imports }: DashboardProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [newCourseName, setNewCourseName] = useState("");
  const [creating, setCreating] = useState(false);
  const [generatingDomainId, setGeneratingDomainId] = useState<string | null>(null);
  const [activeImportId, setActiveImportId] = useState<string | null>(null);
  const [modalDomain, setModalDomain] = useState<DomainPack | null>(null);
  const [activeImport, setActiveImport] = useState<ContentImport | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!generatingDomainId) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(
          activeImportId ? `${API_BASE_URL}/imports/${activeImportId}` : `${API_BASE_URL}/imports`,
          { cache: "no-store" }
        );
        if (!response.ok) return;
        const latest = activeImportId
          ? await readApiJson<ContentImport>(response)
          : (await readApiJson<ContentImport[]>(response)).find((item) => item.domain_id === generatingDomainId);
        if (latest) setActiveImport(latest);
      } catch {
        // Progress polling is best-effort while the upload request is open.
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [activeImportId, generatingDomainId]);

  useEffect(() => {
    if (!activeImport || !["published", "failed", "paused"].includes(activeImport.status)) return;
    setGeneratingDomainId(null);
    if (activeImport.status === "published") {
      setMessage("课程生成完成，刷新页面后可查看最新章节和题目。");
    } else if (activeImport.status === "paused") {
      setMessage("生成已暂停，可以稍后从已保存的段落继续。");
    } else {
      setMessage(activeImport.error || "课程生成失败。");
    }
  }, [activeImport]);

  async function createCourse() {
    const name = newCourseName.trim();
    if (!name) {
      setMessage("请输入课程名称。");
      return;
    }
    setCreating(true);
    setMessage("正在创建课程...");
    try {
      const response = await fetch(`${API_BASE_URL}/domains`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      });
      const payload = await readApiJson<{ detail?: string }>(response);
      if (!response.ok) throw new Error(payload.detail ?? `创建课程失败：${response.status}`);
      window.location.reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "创建课程失败。");
    } finally {
      setCreating(false);
    }
  }

  async function deleteCourse(domain: DomainPack) {
    const ok = window.confirm(`确定删除课程「${domain.name}」吗？章节、题目和学习记录都会删除。`);
    if (!ok) return;
    const response = await fetch(`${API_BASE_URL}/domains/${domain.id}`, { method: "DELETE" });
    if (!response.ok) {
      window.alert(await apiErrorMessage(response, "删除课程失败"));
      return;
    }
    window.location.reload();
  }

  async function submitGenerate() {
    if (!modalDomain) return;
    const targetDomain = modalDomain;
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setMessage("请先选择一个 PDF、DOCX、Markdown 或 TXT 文件。");
      return;
    }

    setGeneratingDomainId(targetDomain.id);
    setActiveImportId(null);
    setActiveImport(null);
    setModalDomain(null);
    setMessage(`正在为「${targetDomain.name}」生成课程...`);
    const form = new FormData();
    form.append("file", file);
    form.append("domain_id", targetDomain.id);

    let started = false;
    try {
      const response = await fetch(`${API_BASE_URL}/imports`, {
        method: "POST",
        body: form
      });
      const payload = await readApiJson<ImportResult & { detail?: string }>(response);
      if (!response.ok) throw new Error(payload.detail ?? `生成失败：${response.status}`);
      const result = payload as ImportResult;
      setActiveImport(result.import_record);
      setActiveImportId(result.import_record.id);
      started = true;
      setMessage(`「${targetDomain.name}」已开始生成，正在解析文件和计算总段数。`);
    } catch (error) {
      try {
        const response = await fetch(`${API_BASE_URL}/imports`, { cache: "no-store" });
        if (response.ok) {
          const latestImports = await readApiJson<ContentImport[]>(response);
          const latestFailed = latestImports.find(
            (item) => item.domain_id === targetDomain.id && item.status === "failed"
          );
          if (latestFailed) {
            setActiveImport(latestFailed);
            setActiveImportId(latestFailed.id);
          }
        }
      } catch {
        // The submit error below is the source of truth.
      }
      setMessage(error instanceof Error ? error.message : "生成失败。");
    } finally {
      if (!started) setGeneratingDomainId(null);
    }
  }

  async function controlImport(importId: string, action: "pause" | "resume") {
    const response = await fetch(`${API_BASE_URL}/imports/${importId}/${action}`, { method: "POST" });
    const payload = await readApiJson<ContentImport & { detail?: string }>(response);
    if (!response.ok) throw new Error(payload.detail ?? `${action} failed: ${response.status}`);
    setActiveImport(payload as ContentImport);
    setActiveImportId(payload.id);
    if (action === "resume") setGeneratingDomainId(payload.domain_id);
    setMessage(action === "pause" ? "已请求暂停，当前 AI 请求结束后会停住。" : "已继续生成，会从已保存的段落接着跑。");
  }

  function latestImportFor(domainId: string) {
    if (activeImport?.domain_id === domainId) return activeImport;
    return imports.find((item) => item.domain_id === domainId);
  }

  return (
    <div className="admin-content">
      <Panel title="课程列表">
        <div className="course-manager-head">
          <p className="panel-subtitle">管理所有课程包。可以新增课程，也可以在课程条目里上传文件重新生成章节和题目。</p>
          <div className="inline-form course-create">
            <input
              value={newCourseName}
              onChange={(event) => setNewCourseName(event.target.value)}
              placeholder="新课程名称"
              disabled={creating}
            />
            <button type="button" onClick={createCourse} disabled={creating}>
              {creating ? "创建中..." : "新增课程"}
            </button>
          </div>
        </div>
        {message && <p className="muted">{message}</p>}
        <div className="course-table">
          <div className="table-head">
            <span>课程</span>
            <span>章节</span>
            <span>题目</span>
            <span>操作</span>
          </div>
          {courseSummaries.length === 0 && (
            <EmptyState title="暂无课程" text="先在这里新增课程，再在课程条目中上传文件生成内容。" />
          )}
          {courseSummaries.map((item) => {
            const courseImport = latestImportFor(item.domain.id);
            return (
              <details className="course-detail" key={item.domain.id} open={item.domain.id === latestDomain?.id}>
                <summary className="course-row">
                  <div>
                    <strong>{item.domain.name}</strong>
                    <p>{item.domain.description}</p>
                    <small>{item.domain.slug}</small>
                  </div>
                  <span>{item.skillCount}</span>
                  <span>{item.questionCount}</span>
                  <div className="course-actions">
                    <span className={item.domain.id === latestDomain?.id ? "pill published" : "pill"}>
                      {item.domain.id === latestDomain?.id ? "最新发布" : item.domain.version}
                    </span>
                    <button
                      type="button"
                      className="secondary small-action"
                      disabled={generatingDomainId !== null}
                      onClick={(event) => {
                        event.preventDefault();
                        setMessage("");
                        setModalDomain(item.domain);
                      }}
                    >
                      生成课程
                    </button>
                    <button
                      type="button"
                      className="text-danger"
                      onClick={(event) => {
                        event.preventDefault();
                        void deleteCourse(item.domain);
                      }}
                    >
                      删除
                    </button>
                  </div>
                </summary>
                <CourseImportProgress
                  item={courseImport}
                  isGenerating={generatingDomainId === item.domain.id}
                  onAction={controlImport}
                />
                <CourseOutline skills={item.skills} />
              </details>
            );
          })}
        </div>
      </Panel>
      {modalDomain && (
        <div className="modal-backdrop" role="presentation">
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="generate-course-title">
            <div className="modal-head">
              <div>
                <p className="eyebrow">生成课程</p>
                <h2 id="generate-course-title">{modalDomain.name}</h2>
              </div>
              <button type="button" className="icon-button" onClick={() => setModalDomain(null)}>
                ×
              </button>
            </div>
            <p className="panel-subtitle">上传 PDF / DOCX / Markdown / TXT，会清空该课程原有章节和题目后重新生成。</p>
            <input ref={fileInputRef} type="file" accept=".pdf,.docx,.md,.txt" />
            <div className="modal-actions">
              <button type="button" className="secondary small-action" onClick={() => setModalDomain(null)}>
                取消
              </button>
              <button type="button" className="small-action primary-action" onClick={submitGenerate}>
                开始生成
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ImportsPanel({ imports }: { imports: ContentImport[] }) {
  const [items, setItems] = useState(imports);

  async function controlImport(importId: string, action: "pause" | "resume") {
    const response = await fetch(`${API_BASE_URL}/imports/${importId}/${action}`, { method: "POST" });
    const payload = await readApiJson<ContentImport & { detail?: string }>(response);
    if (!response.ok) throw new Error(payload.detail ?? `${action} failed: ${response.status}`);
    setItems((current) => current.map((item) => (item.id === payload.id ? (payload as ContentImport) : item)));
  }

  return (
    <div className="admin-content">
      <Panel title="导入记录">
        <ImportList imports={items} onAction={controlImport} />
      </Panel>
    </div>
  );
}

function LearningPanel({ states, evidence }: { states: LearnerState[]; evidence: Evidence[] }) {
  return (
    <div className="admin-content">
      <section className="grid">
        <Panel title="掌握度">
          <div className="stack">
            {states.length === 0 ? (
              <EmptyState title="暂无学习数据" text="App 完成学习或复习后，这里会出现掌握度记录。" />
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

        <Panel title="最近答题记录">
          <div className="stack">
            {evidence.length === 0 ? (
              <EmptyState title="暂无答题记录" text="选择题、复习和“我不会”都会记录在这里。" />
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
    </div>
  );
}

function CourseOutline({ skills }: { skills: Skill[] }) {
  if (skills.length === 0) {
    return <EmptyState title="暂无章节" text="点击该课程的“生成课程”上传文件生成内容。" />;
  }
  return (
    <div className="course-outline">
      {skills.map((skill, index) => (
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
  );
}

function CourseImportProgress({
  item,
  isGenerating,
  onAction
}: {
  item?: ContentImport;
  isGenerating: boolean;
  onAction?: (importId: string, action: "pause" | "resume") => Promise<void>;
}) {
  if (!item && !isGenerating) return null;
  const total = item?.total_segments ?? 0;
  const done = item?.processed_segments ?? 0;
  const percentValue = total > 0 ? Math.round((done / total) * 100) : isGenerating ? 8 : 0;
  const status = item?.status ?? "generating";
  return (
    <div className="course-progress">
      <div className="progress-line">
        <span>{item?.current_step || "准备生成"}</span>
        <strong>{total > 0 ? `${done}/${total}` : "解析中"}</strong>
      </div>
      <div className="progress-track">
        <i style={{ width: `${percentValue}%` }} />
      </div>
      <div className="progress-meta">
        <span className={`pill ${status}`}>{status}</span>
        {item?.filename && <span>{item.filename}</span>}
        {item && onAction && <ImportActionButtons item={item} onAction={onAction} />}
        {item?.error && <span className="error">{item.error}</span>}
      </div>
    </div>
  );
}

function ImportList({
  imports,
  onAction
}: {
  imports: ContentImport[];
  onAction?: (importId: string, action: "pause" | "resume") => Promise<void>;
}) {
  return (
    <div className="stack">
      {imports.length === 0 ? (
        <EmptyState title="还没有导入记录" text="上传文件生成课程后，任务进度和失败原因会显示在这里。" />
      ) : (
        imports.map((item) => (
          <article className="row" key={item.id}>
            <div>
              <strong>{item.filename}</strong>
              <p>{item.domain?.name ?? (item.error || "尚未生成课程")}</p>
              {item.total_segments > 0 && (
                <p>
                  进度：{item.processed_segments}/{item.total_segments} · {item.current_step}
                </p>
              )}
              <small>{formatDate(item.completed_at ?? item.created_at)}</small>
              {item.error && <p className="error">{item.error}</p>}
            </div>
            <div className="import-row-actions">
              <span className={`pill ${item.status}`}>{item.status}</span>
              {onAction && <ImportActionButtons item={item} onAction={onAction} />}
            </div>
          </article>
        ))
      )}
    </div>
  );
}

function ImportActionButtons({
  item,
  onAction
}: {
  item: ContentImport;
  onAction: (importId: string, action: "pause" | "resume") => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const canPause = pausableImportStatuses.has(item.status);
  const canResume = resumableImportStatuses.has(item.status);
  if (!canPause && !canResume) return null;

  async function run(action: "pause" | "resume") {
    setBusy(true);
    try {
      await onAction(item.id, action);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="task-actions">
      {canPause && (
        <button type="button" className="secondary small-action" disabled={busy} onClick={() => void run("pause")}>
          暂停
        </button>
      )}
      {canResume && (
        <button type="button" className="small-action primary-action" disabled={busy} onClick={() => void run("resume")}>
          继续
        </button>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
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

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
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
