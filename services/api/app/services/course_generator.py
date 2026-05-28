import json
import re
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


UNKNOWN_OPTION = "我不会"


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


def generate_course_pack(*, source_text: str, filename: str) -> GeneratedDomainPack:
    if settings.ai_provider.lower() != "openai":
        raise CourseGenerationError("AI_PROVIDER=openai is required for course generation.")
    if not settings.openai_api_key:
        raise CourseGenerationError("OPENAI_API_KEY is required for course generation.")
    if not settings.openai_model:
        raise CourseGenerationError("OPENAI_MODEL is required for course generation.")
    if len(source_text.strip()) < 80:
        raise CourseGenerationError("The uploaded file does not contain enough extractable text.")

    markdown = _generate_text(_build_prompt(source_text=source_text, filename=filename))
    try:
        return _parse_course_markdown(markdown)
    except CourseGenerationError:
        repaired = _generate_text(_build_repair_prompt(markdown))
        return _parse_course_markdown(repaired)


def _generate_text(prompt: str) -> str:
    base_url = settings.openai_base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    response_error: Exception | None = None
    try:
        response = httpx.post(
            f"{base_url}/responses",
            headers=headers,
            json={"model": settings.openai_model, "input": prompt},
            timeout=180,
        )
        if response.status_code != 404:
            response.raise_for_status()
            return _extract_responses_text(response.json())
        response_error = httpx.HTTPStatusError("Responses endpoint returned 404", request=response.request, response=response)
    except httpx.HTTPError as exc:
        response_error = exc

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": settings.openai_model,
                "messages": [
                    {"role": "system", "content": "你是课程生成器。请只输出 Markdown，不要输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=180,
        )
        response.raise_for_status()
        return _extract_chat_text(response.json())
    except httpx.HTTPError as exc:
        detail = f"Responses error: {response_error}; chat/completions error: {exc}"
        raise CourseGenerationError(f"OpenAI generation failed: {detail}") from exc


def _build_prompt(*, source_text: str, filename: str) -> str:
    today = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    excerpt = source_text[:40000]
    truncated_note = "\n材料较长，下面给出 PDF 目录和前 40000 字符。请优先依据目录决定完整课程路线，再用正文补充讲解与题目。" if len(source_text) > len(excerpt) else ""
    return f"""
你是一个移动端碎片化学习课程设计器。请把用户上传的材料生成一个可直接发布的课程包。

文件名：{filename}
默认 slug 前缀：upload_{today}
{truncated_note}

重要要求：
- 只输出 Markdown，不要输出 JSON。
- 课程节点数量由材料内容决定：材料短就少，材料长就多；不要固定成 9 节或 12 节。
- 题目数量由每节内容决定：每节至少 1 道，重点章节可以有多道。
- 每个节点包含 1 段讲解和若干要点。
- 每道题必须有选项“{UNKNOWN_OPTION}”，且“{UNKNOWN_OPTION}”不能是正确答案。
- slug 只能使用小写英文、数字、下划线。
- prerequisites 只能引用前面已经出现过的 skill slug。
- 内容要面向初学者，避免投资建议和交易指令，只讲概念、方法和风险边界。

请严格使用下面的 Markdown 模板：

# 课程包名称

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
{excerpt}
MATERIAL_END>>>
""".strip()


def _build_repair_prompt(markdown: str) -> str:
    return f"""
下面是一段课程 Markdown，但格式不完全符合模板。请修复它。

要求：
- 只输出 Markdown，不要输出 JSON。
- 不要新增课程，不要删除课程。
- 每个课程节点都要有 slug、summary、kind、difficulty、minutes、prerequisites、讲解、要点、选择题。
- 每道题必须有“{UNKNOWN_OPTION}”选项，且正确答案不能是“{UNKNOWN_OPTION}”。
- prerequisites 只能引用前面课程的 slug。

待修复 Markdown：
{markdown[:60000]}
""".strip()


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
        except CourseGenerationError:
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
