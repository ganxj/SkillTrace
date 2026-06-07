"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, type ContentImport, type DomainPack } from "@/lib/api";

type ImportResult = {
  import_record: ContentImport;
  domain: { id: string; name: string; slug: string };
  skill_count: number;
  question_count: number;
};

type CourseImporterProps = {
  domains: DomainPack[];
};

export function CourseImporter({ domains }: CourseImporterProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [selectedDomainId, setSelectedDomainId] = useState(domains.at(-1)?.id ?? "");
  const [newCourseName, setNewCourseName] = useState("");
  const [activeImport, setActiveImport] = useState<ContentImport | null>(null);

  useEffect(() => {
    if (!busy) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/imports`, { cache: "no-store" });
        if (!response.ok) return;
        const imports = (await response.json()) as ContentImport[];
        const latest = imports.find(
          (item) =>
            item.domain_id === selectedDomainId &&
            item.status !== "published" &&
            item.status !== "failed"
        );
        if (latest) setActiveImport(latest);
      } catch {
        // Polling is best-effort while the upload request is still running.
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [busy, selectedDomainId]);

  async function createCourse() {
    const name = newCourseName.trim();
    if (!name) {
      setMessage("请输入课程名称。");
      return;
    }
    setBusy(true);
    setMessage("正在创建课程...");
    try {
      const response = await fetch(`${API_BASE_URL}/domains`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "创建课程失败。");
      setMessage("课程已创建，请刷新后选择该课程上传文件。");
      window.location.reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "创建课程失败。");
    } finally {
      setBusy(false);
    }
  }

  async function clearCourse() {
    if (!selectedDomainId) {
      setMessage("请先选择课程。");
      return;
    }
    setBusy(true);
    setMessage("正在清空该课程的章节和题目...");
    try {
      const response = await fetch(`${API_BASE_URL}/domains/${selectedDomainId}/content`, {
        method: "DELETE"
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "清空课程失败。");
      setMessage("已清空该课程内容，可以重新上传文件生成。");
      window.location.reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "清空课程失败。");
    } finally {
      setBusy(false);
    }
  }

  async function deleteCourse() {
    if (!selectedDomainId) {
      setMessage("请先选择课程。");
      return;
    }
    const selected = domains.find((domain) => domain.id === selectedDomainId);
    const ok = window.confirm(`确定删除课程「${selected?.name ?? selectedDomainId}」吗？章节、题目和学习记录都会删除。`);
    if (!ok) return;
    setBusy(true);
    setMessage("正在删除课程...");
    try {
      const response = await fetch(`${API_BASE_URL}/domains/${selectedDomainId}`, {
        method: "DELETE"
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "删除课程失败。");
      setMessage("课程已删除。");
      window.location.reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "删除课程失败。");
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    const file = inputRef.current?.files?.[0];
    if (!file) {
      setMessage("请先选择一个 PDF、DOCX、Markdown 或 TXT 文件。");
      return;
    }
    if (!selectedDomainId) {
      setMessage("请先选择课程。也可以先新增课程，再上传文件。");
      return;
    }

    setBusy(true);
    setMessage("正在上传、解析图片和文字，并分段生成课程...");
    setResult(null);
    setActiveImport(null);
    const form = new FormData();
    form.append("file", file);
    form.append("domain_id", selectedDomainId);

    try {
      const response = await fetch(`${API_BASE_URL}/imports`, {
        method: "POST",
        body: form
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? `生成失败：${response.status}`);
      }
      setResult(payload as ImportResult);
      setActiveImport((payload as ImportResult).import_record);
      setMessage("课程课件和题目已重新生成。刷新页面后可在课程列表查看。");
      window.location.reload();
    } catch (error) {
      try {
        const response = await fetch(`${API_BASE_URL}/imports`, { cache: "no-store" });
        if (response.ok) {
          const imports = (await response.json()) as ContentImport[];
          const latestFailed = imports.find(
            (item) => item.domain_id === selectedDomainId && item.status === "failed"
          );
          if (latestFailed) setActiveImport(latestFailed);
        }
      } catch {
        // The explicit submit error below is more useful than a polling error.
      }
      setMessage(error instanceof Error ? error.message : "生成失败。");
    } finally {
      setBusy(false);
    }
  }

  const progressTotal = activeImport?.total_segments ?? 0;
  const progressDone = activeImport?.processed_segments ?? 0;
  const progressPercent = progressTotal > 0 ? Math.round((progressDone / progressTotal) * 100) : busy ? 8 : 0;

  return (
    <div className="importer">
      <div className="inline-form">
        <input
          value={newCourseName}
          onChange={(event) => setNewCourseName(event.target.value)}
          placeholder="新课程名称"
          disabled={busy}
        />
        <button type="button" onClick={createCourse} disabled={busy}>
          新增课程
        </button>
      </div>
      <select value={selectedDomainId} onChange={(event) => setSelectedDomainId(event.target.value)} disabled={busy}>
        <option value="">选择课程</option>
        {domains.map((domain) => (
          <option value={domain.id} key={domain.id}>
            {domain.name}
          </option>
        ))}
      </select>
      <input ref={inputRef} type="file" accept=".pdf,.docx,.md,.txt" disabled={busy} />
      <div className="inline-form">
        <button type="button" onClick={submit} disabled={busy}>
          {busy ? "生成中..." : "上传到所选课程并生成"}
        </button>
        <button type="button" className="secondary" onClick={clearCourse} disabled={busy || !selectedDomainId}>
          清空该课程内容
        </button>
      </div>
      <button type="button" className="danger" onClick={deleteCourse} disabled={busy || !selectedDomainId}>
        删除所选课程
      </button>
      {(busy || activeImport) && (
        <div className="progress-box">
          <div className="progress-line">
            <span>{activeImport?.current_step || "准备生成"}</span>
            <strong>
              {progressTotal > 0 ? `${progressDone}/${progressTotal}` : "解析中"}
            </strong>
          </div>
          <div className="progress-track">
            <i style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      )}
      {message && <p className="muted">{message}</p>}
      {result && (
        <div className="result">
          <strong>{result.domain.name}</strong>
          <p>
            {result.domain.slug} · {result.skill_count} 节课 · {result.question_count} 道题
          </p>
        </div>
      )}
    </div>
  );
}
