import logging
from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    fallback: bool = False


class LLMRouterService:
    def __init__(self):
        self.primary_client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            max_retries=0,
        )
        self.fallback_url = settings.FALLBACK_LLM_URL
        self.fallback_model = settings.FALLBACK_MODEL

    async def generate_response(self, messages: list, model: str | None = None) -> LLMResult:
        """Try the primary model, switch to the fallback model on any failure."""
        formatted = [{"role": m.role, "content": m.content} for m in messages]

        # 1. Primary model (Groq)
        try:
            response = await self.primary_client.chat.completions.create(
                model=settings.PRIMARY_MODEL,
                messages=formatted,
                timeout=settings.LATENCY_THRESHOLD_SECONDS,
            )
            usage = response.usage
            return LLMResult(
                content=response.choices[0].message.content,
                model=settings.PRIMARY_MODEL,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            )
        except Exception as primary_error:
            logger.warning("[FALLBACK TRIGGERED] primary model failed: %s", primary_error)

        # 2. Fallback model (Ollama)
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{self.fallback_url}/chat/completions",
                    json={"model": self.fallback_model, "messages": formatted},
                    timeout=120.0,
                )
                r.raise_for_status()
                data = r.json()
                usage = data.get("usage") or {}
                return LLMResult(
                    content=data["choices"][0]["message"]["content"],
                    model=self.fallback_model,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    fallback=True,
                )
        except Exception as fallback_error:
            raise RuntimeError(
                f"Both models failed (primary and fallback). "
                f"Error: {type(fallback_error).__name__}: {fallback_error}"
            )


llm_router_service = LLMRouterService()