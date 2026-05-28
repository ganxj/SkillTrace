from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings


class TutorProviderError(RuntimeError):
    pass


class TutorProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, *, message: str, mode: str, skill_title: str | None = None) -> str:
        raise NotImplementedError


class MockTutorProvider(TutorProvider):
    name = "mock"

    def generate(self, *, message: str, mode: str, skill_title: str | None = None) -> str:
        topic = skill_title or "当前知识点"
        return (
            f"[Mock Tutor/{mode}] 我会围绕“{topic}”帮你做 5 分钟碎片学习。\n\n"
            f"你刚才说：{message}\n\n"
            "建议下一步：先用一句话解释这个概念，再做一道小题验证理解。"
        )


class OpenAITutorProvider(TutorProvider):
    name = "openai"

    def generate(self, *, message: str, mode: str, skill_title: str | None = None) -> str:
        if not settings.openai_api_key:
            raise TutorProviderError("AI_PROVIDER=openai requires OPENAI_API_KEY.")
        if not settings.openai_model:
            raise TutorProviderError("AI_PROVIDER=openai requires OPENAI_MODEL.")

        prompt = (
            "You are an AI learning tutor for a mobile-first fragmented learning system. "
            "Keep replies concise, ask one useful question, and never introduce backtesting "
            "or trading execution features. "
            f"Mode: {mode}. Skill: {skill_title or 'general'}.\n\nUser: {message}"
        )
        return _generate_text(prompt)


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
            timeout=60,
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
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=60,
        )
        response.raise_for_status()
        return _extract_chat_text(response.json())
    except httpx.HTTPError as exc:
        raise TutorProviderError(f"OpenAI generation failed: responses={response_error}; chat/completions={exc}") from exc


def _extract_responses_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if output_text:
        return output_text
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return content["text"]
    return "OpenAI returned an empty response."


def _extract_chat_text(data: dict[str, Any]) -> str:
    choices = data.get("choices", [])
    if not choices:
        return "OpenAI returned an empty response."
    return choices[0].get("message", {}).get("content") or "OpenAI returned an empty response."


def get_tutor_provider() -> TutorProvider:
    provider = settings.ai_provider.lower()
    if provider == "openai":
        return OpenAITutorProvider()
    return MockTutorProvider()
