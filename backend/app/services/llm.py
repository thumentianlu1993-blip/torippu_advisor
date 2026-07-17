import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "Qwen/Qwen2.5-72B-Instruct"


class LLMClient:
    """OpenAI-compatible client for the 硅基流动 aggregated API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or settings.SILICONFLOW_API_KEY
        self.base_url = base_url or "https://api.siliconflow.cn/v1"

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("SILICONFLOW_API_KEY is not configured")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.5,
    ) -> dict[str, Any]:
        """Generate a JSON object using structured output."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s", content[:500])
            raise RuntimeError("LLM returned invalid JSON") from exc


llm_client = LLMClient()
