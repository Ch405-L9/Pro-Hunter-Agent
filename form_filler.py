import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_IDENTITY = Path(__file__).resolve().parent / "config" / "identity.yaml"


class FormFiller:
    def __init__(self, identity: dict = None, identity_path: str = None,
                 ollama_model: str = "qwen2.5:14b", ollama_base_url: str = "http://localhost:11434"):
        if identity:
            self.identity = identity.get("identity", identity)
        else:
            path = identity_path or str(_DEFAULT_IDENTITY)
            with open(path, "r") as f:
                self.identity = yaml.safe_load(f).get("identity", {})

        self.ollama_model = ollama_model
        self.ollama_base_url = ollama_base_url

    def _build_llm(self):
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=self.ollama_model, base_url=self.ollama_base_url)
        except ImportError:
            logger.warning("langchain-ollama not installed; falling back to langchain-openai")
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o")

    async def fill_application(self, url: str, dry_run: bool = True):
        from browser_use import Agent
        llm = self._build_llm()

        personal = self.identity.get("personal", self.identity)
        business = self.identity.get("business", {})

        task = f"""Navigate to {url}.
Fill the job application form using this identity:
- Full Name: {personal.get('full_name', '')}
- Email: {personal.get('email', '')}
- Phone: {personal.get('phone', '')}
- Address: {personal.get('address', {}).get('street', '')}, {personal.get('address', {}).get('city', '')}, {personal.get('address', {}).get('state', '')} {personal.get('address', {}).get('zip', '')}
- Company: {business.get('company_name', '')}
- UEI: {business.get('uei', '')}

{'DO NOT click submit. Fill fields only and take a screenshot.' if dry_run else 'Fill all fields and submit.'}"""

        agent = Agent(task=task, llm=llm)
        result = await agent.run()
        logger.info("FormFiller %s for %s", "dry-run complete" if dry_run else "submitted", url)
        return result
