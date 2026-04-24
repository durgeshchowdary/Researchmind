import logging

import httpx

from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class LLMClient:
    def is_configured(self) -> bool:
        return bool(settings.openai_base_url and settings.openai_api_key and settings.openai_model)

    async def generate(self, prompt: str) -> str | None:
        if not self.is_configured():
            return None
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.openai_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Answer only from the provided context. If unsupported, say so clearly.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.1,
                    }
                )
                response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            logger.exception("LLM generation failed; falling back to extractive answer")
            return None


llm_client = LLMClient()
