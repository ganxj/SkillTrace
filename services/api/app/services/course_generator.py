from __future__ import annotations

import json
import re
from time import sleep
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.services.content_parser import ExtractedContent, ExtractedImage


UNKNOWN_OPTION = "我不会"
MAX_SEGMENT_CHARS = 3600  # 增加到3600，减少分段数，提升生成效率
MAX_SEGMENT_IMAGES = 2
MAX_AI_ATTEMPTS = 3


class CourseGenerationError(RuntimeError):
    pass


class GeneratedQuestion(BaseModel):
    prompt: str = Field(min_length=4)
    options: list[str] = Field(min_length=2, max_length=8)
    correct_index: int = Field(ge=0)
    explanation: str = Field(min_length=4)

    @field_validator("options")
    @classmethod
    def must_include_unknown(cls, value: list[str]) -> list[str]:
        if UNKNOWN_OPTION not in value:
            raise ValueError(f'Each question must include the option "{UNKNOWN_OPTION}".')
        return value

    def model_post_init(self, __context: Any) -> None:
        if self.correct_index >= len(self.options):
            raise ValueError("correct_index is out of range.")
        if self.options[self.correct_index] == UNKNOWN_OPTION:
            raise ValueError(f'"{UNKNOWN_OPTION}" cannot be the correct answer.')


class GeneratedSkill(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9_]+$")
    title: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=4)
    kind: str = "concept"
    difficulty: int = Field(default=1, ge=1, le=5)
    estimated_minutes: int = Field(default=6, ge=3, le=60)
    order_index: int = Field(ge=1)
    prerequisites: list[str] = Field(default_factory=list)
    lesson_explain: str = Field(min_length=20)
    key_points: list[str] = Field(min_length=1, max_length=5)
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=20)


class GeneratedDomainPack(BaseModel):
    slug: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=100)
    version: str = Field(default="0.1.0", max_length=40)
    description: str = Field(default="")
    skills: list[GeneratedSkill] = Field(min_length=1, max_length=120)

    @field_validator("skills")
    @classmethod
    def validate_skill_graph(cls, skills: list[GeneratedSkill]) -> list[GeneratedSkill]:
        slugs = [skill.slug for skill in skills]
        if len(slugs) != len(set(slugs)):
            raise ValueError("Skill slugs must be unique.")
        seen: set[str] = set()
        for skill in sorted(skills, key=lambda item: item.order_index):
            invalid = [slug for slug in skill.prerequisites if slug not in seen]
            if invalid:
                raise ValueError(f"Prerequisites must reference earlier skills: {', '.join(invalid)}")
            seen.add(skill.slug)
        return skills


def generate_course_pack(
    *,
    source_text: str | None = None,
    content: ExtractedContent | None = None,
    filename: str,
    course_name: str | None = None,
    progress_callback: Any | None = None,
) -> GeneratedDomainPack:
    if settings.ai_provider.lower() != "openai":
        raise CourseGenerationError("AI_PROVIDER=openai is required for course generation.")
    if not settings.openai_api_key:
        raise CourseGenerationError("OPENAI_API_KEY is required for course generation.")
    if not settings.openai_model:
        raise CourseGenerationError("OPENAI_MODEL is required for course generation.")
    extracted = content or ExtractedContent(text=source_text or "", pages=[], images=[])
    if len(extracted.text.strip()) < 80:
        raise CourseGenerationError("The uploaded file does not contain enough extractable text.")

    segments = _build_segments(extracted)
    if progress_callback:
        progress_callback(total=len(segments), processed=0, step="已解析文件，开始分段生成")

    packs: list[GeneratedDomainPack] = []
    context_summary = ""
    for index, segment in enumerate(segments, start=1):
        if progress_callback:
            progress_callback(total=len(segments), processed=index - 1, step=f"正在生成第 {index}/{len(segments)} 段")
        prompt = _build_segment_prompt(
            segment=segment,
            filename=filename,
            course_name=course_name,
            index=index,
            total=len(segments),
            previous_context=context_summary,
        )
        pack = _generate_segment_pack(
            prompt=prompt,
            segment=segment,
            images=segment.images,
            course_name=course_name,
            segment_index=index,
            segment_total=len(segments),
            progress_callback=progress_callback,
        )
        packs.append(pack)
        context_summary = _summarize_generated_context(packs)
        if progress_callback:
            progress_callback(total=len(segments), processed=index, step=f"已完成第 {index}/{len(segments)} 段")

    if progress_callback:
        progress_callback(total=len(segments), processed=len(segments), step="正在合并课程节点")
    return _merge_segment_packs(packs, course_name=course_name)


def _generate_text(
    prompt: str,
    *,
    images: list[ExtractedImage] | None = None,
    progress_callback: Any | None = None,
    progress_total: int = 0,
    progress_processed: int = 0,
    progress_step: str = "正在请求 AI",
) -> str:
    base_url = settings.openai_base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(1, MAX_AI_ATTEMPTS + 1):
        if progress_callback:
            progress_callback(
                total=progress_total,
                processed=progress_processed,
                step=f"{progress_step}，AI 请求第 {attempt}/{MAX_AI_ATTEMPTS} 次",
            )
        try:
            response = _post_chat_completion(base_url=base_url, headers=headers, prompt=prompt, images=images or [])
            return _extract_chat_text(_response_json(response))
        except (httpx.HTTPError, CourseGenerationError, ValueError) as exc:
            last_error = exc
            if attempt < MAX_AI_ATTEMPTS:
                if progress_callback:
                    progress_callback(
                        total=progress_total,
                        processed=progress_processed,
                        step=f"{progress_step}失败，准备重试第 {attempt + 1}/{MAX_AI_ATTEMPTS} 次：{_http_error_detail(exc)}",
                    )
                sleep(attempt * 2)
                continue
            break

    raise CourseGenerationError(
        f"OpenAI generation failed after {MAX_AI_ATTEMPTS} attempts: {_http_error_detail(last_error)}"
    ) from last_error


def _generate_segment_pack(
    *,
    prompt: str,
    segment: CourseSegment,
    images: list[ExtractedImage],
    course_name: str | None,
    segment_index: int,
    segment_total: int,
    progress_callback: Any | None,
) -> GeneratedDomainPack:
    markdown = ""
    last_error: CourseGenerationError | None = None
    for format_attempt in range(1, MAX_AI_ATTEMPTS + 1):
        if format_attempt == 1:
            ai_prompt = prompt
            step = f"正在生成第 {segment_index}/{segment_total} 段 Markdown"
        else:
            ai_prompt = _build_repair_prompt(markdown, str(last_error))
            step = f"正在修复第 {segment_index}/{segment_total} 段 Markdown 格式，第 {format_attempt}/{MAX_AI_ATTEMPTS} 轮"

        markdown = _generate_text(
            ai_prompt,
            images=images if format_attempt == 1 else [],
            progress_callback=progress_callback,
            progress_total=segment_total,
            progress_processed=segment_index - 1,
            progress_step=step,
        )
        markdown = _ensure_course_header(markdown, course_name=course_name)
        try:
            return _parse_course_markdown(markdown)
        except CourseGenerationError as exc:
            last_error = exc
            if progress_callback and format_attempt < MAX_AI_ATTEMPTS:
                progress_callback(
                    total=segment_total,
                    processed=segment_index - 1,
                    step=(
                        f"第 {segment_index}/{segment_total} 段 Markdown 解析失败，"
                        f"准备修复第 {format_attempt + 1}/{MAX_AI_ATTEMPTS} 轮：{exc}"
                    ),
                )

    if progress_callback:
        progress_callback(
            total=segment_total,
            processed=segment_index - 1,
            step=f"第 {segment_index}/{segment_total} 段多次生成跑偏，使用保底课程节点继续生成",
        )
    return _fallback_segment_pack(
        segment=segment,
        course_name=course_name,
        segment_index=segment_index,
        parse_error=str(last_error) if last_error else "",
        model_output=markdown,
    )


def _post_chat_completion(
    *,
    base_url: str,
    headers: dict[str, str],
    prompt: str,
    images: list[ExtractedImage],
) -> httpx.Response:
    response = httpx.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json={
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "你是课程生成器。请只输出 Markdown，不要输出 JSON。"},
                {"role": "user", "content": _chat_content(prompt, images)},
            ],
            "temperature": 0.2,
            "max_tokens": 4000,
        },
        timeout=180,
    )
    response.raise_for_status()
    return response


def _fallback_segment_pack(
    *,
    segment: CourseSegment,
    course_name: str | None,
    segment_index: int,
    parse_error: str,
    model_output: str,
) -> GeneratedDomainPack:
    title = _fallback_title(segment.text, segment_index)
    slug_base = f"fallback_{segment_index}_{_slugify(title)}"
    excerpt = _compact_excerpt(segment.text, 900)
    lesson = (
        f"本节来自上传材料第 {segment_index} 个片段。模型未能稳定生成完整 Markdown，"
        f"系统已保留该片段的核心内容并整理为可复习的学习节点。\n\n"
        f"材料摘录：\n{excerpt}"
    )
    if parse_error:
        lesson += f"\n\n生成修复提示：{parse_error[:300]}"
    if model_output:
        lesson += f"\n\n模型最后一次输出摘录：{_compact_excerpt(model_output, 300)}"

    skill = GeneratedSkill(
        slug=_clean_slug(slug_base),
        title=title,
        summary=f"理解材料片段 {segment_index} 中的关键规范、示例和边界。",
        kind="concept",
        difficulty=2,
        estimated_minutes=6,
        order_index=1,
        prerequisites=[],
        lesson_explain=lesson,
        key_points=[
            "先识别材料片段中的规则、示例和例外情况。",
            "代码示例应服务于规范理解，不应只记忆输出结果。",
            "遇到边界条件时，要回到原文语境判断适用范围。",
        ],
        questions=[
            GeneratedQuestion(
                prompt="学习这类规范材料时，最稳妥的做法是什么？",
                options=[
                    "只记住代码片段的输出结果",
                    "结合原文语境理解规则、示例和边界条件",
                    UNKNOWN_OPTION,
                ],
                correct_index=1,
                explanation="规范类内容需要理解适用场景和边界，不能只背单个示例。",
            )
        ],
    )
    return GeneratedDomainPack(
        slug=f"fallback_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{segment_index}",
        name=course_name or "上传课程",
        version="0.1.0",
        description="由上传材料生成的课程片段。",
        skills=[skill],
    )


def _http_error_detail(error: Exception | None) -> str:
    if error is None:
        return "none"
    if isinstance(error, httpx.HTTPStatusError):
        body = error.response.text[:1000] if error.response is not None else ""
        return f"{error} body={body}"
    return str(error)


def _response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        body = response.text[:1000]
        raise CourseGenerationError(f"chat/completions returned non-JSON body: {body}") from exc
    if not isinstance(data, dict):
        raise CourseGenerationError("chat/completions returned a non-object JSON response.")
    return data


def _responses_payload(prompt: str, images: list[ExtractedImage]) -> dict[str, Any]:
    if not images:
        return {"model": settings.openai_model, "input": prompt}
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    for image in images:
        content.append({"type": "input_image", "image_url": image.data_url})
    return {"model": settings.openai_model, "input": [{"role": "user", "content": content}]}


def _chat_content(prompt: str, images: list[ExtractedImage]) -> str | list[dict[str, Any]]:
    if not images:
        return prompt
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": image.data_url, "detail": "low"}})
    return content


class CourseSegment(BaseModel):
    index: int
    text: str
    pages: list[int] = Field(default_factory=list)
    images: list[ExtractedImage] = Field(default_factory=list)


def _build_segments(content: ExtractedContent) -> list[CourseSegment]:
    if content.pages:
        segments: list[CourseSegment] = []
        current_parts: list[str] = []
        current_pages: list[int] = []
        current_images: list[ExtractedImage] = []

        def flush() -> None:
            nonlocal current_parts, current_pages, current_images
            if not current_parts:
                return
            segments.append(
                CourseSegment(
                    index=len(segments) + 1,
                    text="\n\n".join(current_parts),
                    pages=current_pages,
                    images=current_images,
                )
            )
            current_parts = []
            current_pages = []
            current_images = []

        for page in content.pages:
            page_chunks = _split_text_chunks(page.text)
            if not page_chunks:
                if page.images:
                    if current_parts and len(current_images) + len(page.images) > MAX_SEGMENT_IMAGES:
                        flush()
                    current_pages.append(page.page_number)
                    current_images.extend(page.images[:MAX_SEGMENT_IMAGES])
                continue
            for chunk_index, chunk in enumerate(page_chunks, start=1):
                page_label = f"[第{page.page_number}页"
                if len(page_chunks) > 1:
                    page_label += f"，片段{chunk_index}/{len(page_chunks)}"
                page_text = f"{page_label}]\n{chunk}".strip()
                current_text_length = sum(len(part) for part in current_parts)
                chunk_images = page.images[:MAX_SEGMENT_IMAGES] if chunk_index == 1 else []
                next_image_count = len(current_images) + len(chunk_images)
                if current_parts and (
                    current_text_length + len(page_text) > MAX_SEGMENT_CHARS
                    or next_image_count > MAX_SEGMENT_IMAGES
                ):
                    flush()
                current_parts.append(page_text)
                if page.page_number not in current_pages:
                    current_pages.append(page.page_number)
                current_images.extend(chunk_images)
        flush()
        return segments or [CourseSegment(index=1, text=content.text[:MAX_SEGMENT_CHARS], images=content.images[:MAX_SEGMENT_IMAGES])]

    paragraphs = [chunk for part in re.split(r"\n\s*\n", content.text) for chunk in _split_text_chunks(part)]
    segments: list[CourseSegment] = []
    current: list[str] = []
    for paragraph in paragraphs:
        if current and sum(len(part) for part in current) + len(paragraph) > MAX_SEGMENT_CHARS:
            segments.append(CourseSegment(index=len(segments) + 1, text="\n\n".join(current)))
            current = []
        current.append(paragraph)
    if current:
        segments.append(CourseSegment(index=len(segments) + 1, text="\n\n".join(current)))
    return segments or [CourseSegment(index=1, text=content.text[:MAX_SEGMENT_CHARS])]


def _split_text_chunks(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    current = ""
    sentences = [item.strip() for item in re.split(r"(?<=[。！？.!?；])\s+", text) if item.strip()]
    if len(sentences) <= 1:
        sentences = [text[index : index + MAX_SEGMENT_CHARS] for index in range(0, len(text), MAX_SEGMENT_CHARS)]
    for sentence in sentences:
        if len(sentence) > MAX_SEGMENT_CHARS:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(sentence[index : index + MAX_SEGMENT_CHARS] for index in range(0, len(sentence), MAX_SEGMENT_CHARS))
            continue
        if current and len(current) + len(sentence) + 1 > MAX_SEGMENT_CHARS:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current}\n{sentence}".strip() if current else sentence
    if current:
        chunks.append(current.strip())
    return chunks


def _fallback_title(text: str, segment_index: int) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        cleaned = re.sub(r"^[#\-\*\d\.\s]+", "", line).strip()
        if 4 <= len(cleaned) <= 60 and not _looks_like_code(cleaned):
            return cleaned[:60]
    return f"材料片段 {segment_index} 的规范要点"


def _compact_excerpt(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def _looks_like_code(text: str) -> bool:
    code_markers = (";", "{", "}", "()", "String ", "public ", "class ", "System.out", "return ")
    return any(marker in text for marker in code_markers)


def _build_segment_prompt(
    *,
    segment: CourseSegment,
    filename: str,
    course_name: str | None,
    index: int,
    total: int,
    previous_context: str,
) -> str:
    today = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    image_note = _image_note(segment.images)
    context_note = previous_context or "这是第一段，暂无前文生成摘要。"
    name_hint = course_name or "课程包名称"
    return f"""
你是一个移动端碎片化学习课程设计器。请把用户上传的材料生成一个可直接发布的课程包。

文件名：{filename}
目标课程名称：{name_hint}
默认 slug 前缀：upload_{today}
当前材料段：第 {index}/{total} 段
当前段覆盖页码：{', '.join(str(page) for page in segment.pages) if segment.pages else '未提供页码'}

前文生成摘要：
{context_note}

图片说明：
{image_note}

重要要求：
- 只输出 Markdown，不要输出 JSON。
- 输出第一行必须是 "# {name_hint}"，不要在它前面添加解释、代码、答案或寒暄。
- 不要直接回答材料中的示例题、代码输出题或练习题；这些内容只能被改写成课程讲解、要点和选择题。
- 你现在只处理整篇材料中的第 {index}/{total} 段，要和前文摘要衔接，不要重复前面已经生成过的课程节点。
- 本段如果包含图片，图片已经作为多模态输入提供给你；请结合图片内容生成讲解、要点和题目，并在相关讲解中说明图片来自哪一页。
- 课程节点数量由当前段内容决定：内容少就少，内容多就多；不要固定成 9 节或 12 节。
- 当前段通常生成 2 到 4 个高质量课程节点即可；只有当本段确实包含多个独立大主题时才超过 4 个。
- 题目数量由每节内容决定：每节至少 1 道，重点章节可以有多道。
- 每个节点包含 1 段讲解和若干要点。
- 每道题必须有选项“{UNKNOWN_OPTION}”，且“{UNKNOWN_OPTION}”不能是正确答案；如果无法判断正确答案，请重写题目，不要把“{UNKNOWN_OPTION}”设为答案。
- slug 只能使用小写英文、数字、下划线。
- prerequisites 只能引用前面已经出现过的 skill slug。
- 内容要面向初学者，避免投资建议和交易指令，只讲概念、方法和风险边界。

请严格使用下面的 Markdown 模板：

# {name_hint}

slug: upload_{today}
version: 0.1.0
description: 一句话课程包简介

## 1. 课程标题

slug: upload_{today}_first_topic
summary: 一句话摘要
kind: concept
difficulty: 1
minutes: 6
prerequisites: none

### 讲解
面向初学者的一段讲解。

### 要点
- 要点1
- 要点2

### 选择题
题目：题干
A. 选项A
B. 选项B
C. {UNKNOWN_OPTION}
答案：A
解析：答案解释

题目：第二道题题干
A. 选项A
B. 选项B
C. {UNKNOWN_OPTION}
答案：B
解析：答案解释

材料正文：
<<<MATERIAL_START
{segment.text}
MATERIAL_END>>>
""".strip()


def _image_note(images: list[ExtractedImage]) -> str:
    if not images:
        return "本段没有从 PDF 中提取到图片。"
    return "\n".join(
        f"- 图片 {index}: 来自 PDF 第 {image.page_number} 页，文件名 {image.name}，已作为图片输入提供。"
        for index, image in enumerate(images, start=1)
    )


def _summarize_generated_context(packs: list[GeneratedDomainPack]) -> str:
    skills = [skill for pack in packs for skill in sorted(pack.skills, key=lambda item: item.order_index)]
    lines = [f"- {skill.slug}: {skill.title}，{skill.summary}" for skill in skills[-20:]]
    return "\n".join(lines)


def _merge_segment_packs(packs: list[GeneratedDomainPack], *, course_name: str | None) -> GeneratedDomainPack:
    if not packs:
        raise CourseGenerationError("No course segments were generated.")
    base = packs[0]
    merged_skills: list[GeneratedSkill] = []
    seen: set[str] = set()
    for pack in packs:
        for skill in sorted(pack.skills, key=lambda item: item.order_index):
            slug = skill.slug
            if slug in seen:
                slug = _unique_slug(slug, seen)
            seen.add(slug)
            prereqs = [item for item in skill.prerequisites if item in seen]
            merged_skills.append(
                skill.model_copy(
                    update={
                        "slug": slug,
                        "order_index": len(merged_skills) + 1,
                        "prerequisites": prereqs,
                    }
                )
            )
    return GeneratedDomainPack(
        slug=base.slug,
        name=course_name or base.name,
        version=base.version,
        description=base.description,
        skills=merged_skills,
    )


def _unique_slug(slug: str, seen: set[str]) -> str:
    index = 2
    candidate = f"{slug}_{index}"
    while candidate in seen:
        index += 1
        candidate = f"{slug}_{index}"
    return candidate


def _build_repair_prompt(markdown: str, parse_error: str = "") -> str:
    return f"""
下面是一段课程 Markdown，但格式不完全符合模板。请修复它。

要求：
- 只输出 Markdown，不要输出 JSON。
- 第一行必须是 "# 课程包名称" 形式的一级标题。
- 如果待修复内容只是代码、答案、解释片段或普通文本，请不要延续它，必须重写成完整课程 Markdown。
- 不要新增课程，不要删除课程。
- 每个课程节点都要有 slug、summary、kind、difficulty、minutes、prerequisites、讲解、要点、选择题。
- 每道题必须有“{UNKNOWN_OPTION}”选项，且正确答案不能是“{UNKNOWN_OPTION}”。
- prerequisites 只能引用前面课程的 slug。

解析错误：
{parse_error or "未提供"}

待修复 Markdown：
{markdown[:60000]}
""".strip()


def _ensure_course_header(markdown: str, *, course_name: str | None) -> str:
    text = _strip_markdown_fence(markdown)
    if re.search(r"^#\s+.+?$", text, flags=re.MULTILINE):
        return text
    if not re.search(r"^##\s+", text, flags=re.MULTILINE):
        return text
    slug = f"upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    name = course_name or "课程包"
    return f"# {name}\n\nslug: {slug}\nversion: 0.1.0\ndescription: {name}\n\n{text}".strip()


def _parse_course_markdown(markdown: str) -> GeneratedDomainPack:
    text = _strip_markdown_fence(markdown)
    title_match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if not title_match:
        raise CourseGenerationError("Generated Markdown is missing course title.")

    header = text[: title_match.end()]
    after_title = text[title_match.end() :]
    first_skill = re.search(r"^##\s+\d+\.?\s+(.+?)\s*$", after_title, flags=re.MULTILINE)
    meta_block = after_title[: first_skill.start()] if first_skill else after_title

    name = title_match.group(1).strip()
    domain_slug = _clean_slug(_read_meta(meta_block, "slug") or f"upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    version = _read_meta(meta_block, "version") or "0.1.0"
    description = _read_meta(meta_block, "description") or name

    section_pattern = re.compile(r"^##\s+(?:(?:课程|第)?\s*(\d+)\s*[\.、：:]?)?\s*(.+?)\s*$", flags=re.MULTILINE)
    matches = list(section_pattern.finditer(text))
    if not matches:
        raise CourseGenerationError("Generated Markdown is missing skill sections.")

    skills: list[GeneratedSkill] = []
    seen_slugs: set[str] = set()
    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        order_index = int(match.group(1) or (index + 1))
        title = match.group(2).strip()
        title = re.sub(r"^课程\s*\d+\s*[：:]\s*", "", title).strip()
        skill = _parse_skill_section(
            title=title,
            body=body,
            order_index=order_index,
            default_slug=f"{domain_slug}_{_slugify(title)}",
            seen_slugs=seen_slugs,
        )
        seen_slugs.add(skill.slug)
        skills.append(skill)

    return GeneratedDomainPack(
        slug=domain_slug,
        name=name,
        version=version,
        description=description,
        skills=skills,
    )


def _parse_skill_section(
    *,
    title: str,
    body: str,
    order_index: int,
    default_slug: str,
    seen_slugs: set[str],
) -> GeneratedSkill:
    slug = _clean_slug(_read_meta(body, "slug") or default_slug)
    summary = _read_meta(body, "summary") or title
    kind = _read_meta(body, "kind") or "concept"
    difficulty = _parse_int(_read_meta(body, "difficulty"), default=1, low=1, high=5)
    minutes = _parse_int(_read_meta(body, "minutes"), default=6, low=3, high=20)
    prerequisites = _parse_prerequisites(_read_meta(body, "prerequisites"), seen_slugs)
    lesson = _section_text(body, "讲解")
    key_points = _section_bullets(body, "要点")
    questions = _parse_questions(_section_text(body, "选择题"))

    if not lesson:
        raise CourseGenerationError(f"Skill {slug} is missing lesson text.")
    if not key_points:
        raise CourseGenerationError(f"Skill {slug} is missing key points.")

    return GeneratedSkill(
        slug=slug,
        title=title,
        summary=summary,
        kind=kind,
        difficulty=difficulty,
        estimated_minutes=minutes,
        order_index=order_index,
        prerequisites=prerequisites,
        lesson_explain=lesson,
        key_points=key_points[:5],
        questions=questions,
    )


def _parse_questions(text: str) -> list[GeneratedQuestion]:
    starts = list(re.finditer(r"(?:^|\n)(?:#{4,}\s*问题\s*\d+.*\n)?\s*题目[:：]\s*", text))
    if not starts:
        starts = list(re.finditer(r"(?:^|\n)#{4,}\s*问题\s*\d+.*", text))
    if not starts:
        raise CourseGenerationError("Skill is missing questions.")
    questions: list[GeneratedQuestion] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end].strip()
        try:
            questions.append(_parse_question(block))
        except (CourseGenerationError, ValueError):
            continue
    if not questions:
        raise CourseGenerationError("Skill has no complete questions.")
    return questions[:20]


def _parse_question(text: str) -> GeneratedQuestion:
    prompt_match = re.search(r"题目[:：]\s*(.+)", text)
    if prompt_match:
        prompt = prompt_match.group(1).strip()
    else:
        heading_match = re.search(r"^#{4,}\s*问题\s*\d+\s*(.*)$", text, flags=re.MULTILINE)
        prompt = heading_match.group(1).strip() if heading_match and heading_match.group(1).strip() else ""
        if not prompt:
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            lines = [line for line in lines if not line.startswith("#") and not line.startswith("**选项")]
            prompt = lines[0] if lines else ""
    if not prompt:
        raise CourseGenerationError("Question is missing prompt.")

    options: list[str] = []
    labels: list[str] = []
    for label, option in re.findall(r"^\s*(?:[-*]\s*)?([A-H])[\.\、]\s*(.+?)\s*$", text, flags=re.MULTILINE):
        labels.append(label)
        options.append(option.strip())
    if UNKNOWN_OPTION not in options:
        options.append(UNKNOWN_OPTION)
        labels.append(chr(ord("A") + len(labels)))

    answer_match = re.search(r"\*{0,2}答案[:：]\*{0,2}\s*([A-H])", text)
    if not answer_match:
        raise CourseGenerationError("Question is missing answer.")
    answer = answer_match.group(1)
    if answer not in labels:
        raise CourseGenerationError("Question answer does not match options.")
    correct_index = labels.index(answer)

    explanation_match = re.search(r"\*{0,2}解析[:：]\*{0,2}\s*(.+)", text, flags=re.DOTALL)
    explanation = explanation_match.group(1).strip() if explanation_match else "请回到讲解部分复习这个概念。"
    explanation = re.split(r"\n#{2,3}\s+", explanation)[0].strip()

    return GeneratedQuestion(
        prompt=prompt,
        options=options,
        correct_index=correct_index,
        explanation=explanation,
    )


def _read_meta(text: str, key: str) -> str:
    match = re.search(rf"^\s*\*{{0,2}}{re.escape(key)}\*{{0,2}}\s*[:：]\s*(.+?)\s*$", text, flags=re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _section_text(text: str, heading: str) -> str:
    match = re.search(rf"^###\s+{re.escape(heading)}\s*$", text, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^###\s+", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def _section_bullets(text: str, heading: str) -> list[str]:
    section = _section_text(text, heading)
    bullets = [item.strip() for item in re.findall(r"^\s*[-*]\s+(.+?)\s*$", section, flags=re.MULTILINE)]
    if bullets:
        return bullets
    return [line.strip() for line in section.splitlines() if line.strip()]


def _parse_prerequisites(value: str, seen_slugs: set[str]) -> list[str]:
    cleaned = value.strip().strip("[]")
    if not cleaned or cleaned.lower() in {"none", "null", "无", "[]"}:
        return []
    items = [item.strip().strip("`'\"") for item in re.split(r"[,，、]", cleaned) if item.strip()]
    return [_clean_slug(item) for item in items if _clean_slug(item) in seen_slugs]


def _parse_int(value: str, *, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


def _clean_slug(value: str) -> str:
    slug = _slugify(value)
    return slug[:80] or f"upload_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def _strip_markdown_fence(text: str) -> str:
    match = re.search(r"```(?:markdown|md)?\s*(.*?)```", text, flags=re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def _extract_responses_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if output_text:
        return output_text
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(content["text"])
    if not parts:
        raise CourseGenerationError("OpenAI returned an empty response.")
    return "\n".join(parts)


def _extract_chat_text(data: dict[str, Any]) -> str:
    choices = data.get("choices", [])
    if not choices:
        raise CourseGenerationError("chat/completions returned no choices.")
    content = choices[0].get("message", {}).get("content")
    if not content:
        raise CourseGenerationError("chat/completions returned an empty message.")
    return content


def generated_pack_to_json(pack: GeneratedDomainPack) -> str:
    return json.dumps(pack.model_dump(), ensure_ascii=False)
