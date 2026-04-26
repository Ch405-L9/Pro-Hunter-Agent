import logging
from scrapers.base import FetchResult

logger = logging.getLogger(__name__)


class BrowserUseClient:
    """
    LLM-driven browser automation via browser-use.
    Uses local Ollama model by default (langchain-ollama).
    Falls back to langchain-openai if ollama_model is None and openai_model is set.
    """

    def __init__(self, ollama_model: str = "qwen2.5:14b", ollama_base_url: str = "http://localhost:11434",
                 openai_model: str = None):
        self.ollama_model = ollama_model
        self.ollama_base_url = ollama_base_url
        self.openai_model = openai_model

    def _build_llm(self):
        if self.ollama_model:
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(model=self.ollama_model, base_url=self.ollama_base_url)
            except ImportError:
                logger.warning("langchain-ollama not installed; trying langchain-openai")

        if self.openai_model:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=self.openai_model)

        raise RuntimeError("No LLM backend available for BrowserUse")

    async def scrape(self, url: str) -> FetchResult:
        try:
            from browser_use import Agent
            llm = self._build_llm()
            agent = Agent(
                task=f"Navigate to {url} and extract the full job description, title, company name, location, salary if shown, and required skills.",
                llm=llm,
            )
            result = await agent.run()
            content = str(result.final_result()) if result else ""
            if not content.strip():
                return FetchResult(status="failed", method_used="browseruse", content="", error="Empty result")
            return FetchResult(status="ok", method_used="browseruse", content=content)
        except Exception as e:
            logger.warning("BrowserUse error for %s: %s", url, e)
            return FetchResult(status="failed", method_used="browseruse", content="", error=str(e))
