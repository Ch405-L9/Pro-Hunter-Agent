import httpx
import logging
from typing import List

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, model: str = "qwen2.5:14b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if json_mode:
            payload["format"] = "json"
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/api/generate", json=payload, timeout=120.0)
            r.raise_for_status()
            return r.json()["response"]

    async def embed(self, text: str) -> List[float]:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=60.0,
            )
            r.raise_for_status()
            return r.json()["embedding"]
