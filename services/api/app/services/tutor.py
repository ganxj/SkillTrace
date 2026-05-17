from abc import ABC, abstractmethod

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
            f"[Mock Tutor/{mode}] 我会围绕「{topic}」帮你做 5 分钟碎片学习。\n\n"
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
        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.openai_model, "input": prompt},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        output_text = data.get("output_text")
        if output_text:
            return output_text
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    return content["text"]
        return "OpenAI returned an empty response."


def get_tutor_provider() -> TutorProvider:
    provider = settings.ai_provider.lower()
    if provider == "openai":
        return OpenAITutorProvider()
    return MockTutorProvider()

