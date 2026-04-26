import os
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class CloudLLMClient:
    """Claude or OpenAI fallback — only for tasks local models can't handle."""

    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        kwargs = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
