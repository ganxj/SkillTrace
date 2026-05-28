"use client";

import { useRef, useState } from "react";
import { API_BASE_URL, type ContentImport } from "@/lib/api";

type ImportResult = {
  import_record: ContentImport;
  domain: { name: string; slug: string };
  skill_count: number;
  question_count: number;
};

export function CourseImporter() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);

  async function submit() {
    const file = inputRef.current?.files?.[0];
    if (!file) {
      setMessage("请先选择一个 PDF、DOCX、Markdown 或 TXT 文件。");
      return;
    }

    setBusy(true);
    setMessage("正在上传、解析并生成课程包，长 PDF 可能需要几分钟...");
    setResult(null);
    const form = new FormData();
    form.append("file", file);

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
      setMessage("课程包已生成并发布。刷新页面后可在课程列表中查看。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "生成失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="importer">
      <input ref={inputRef} type="file" accept=".pdf,.docx,.md,.txt" disabled={busy} />
      <button type="button" onClick={submit} disabled={busy}>
        {busy ? "生成中..." : "上传并生成课程"}
      </button>
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
