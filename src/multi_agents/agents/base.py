from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from abc import ABC, abstractmethod

from src.core.config import get_settings
from src.core.logger import setup_logger
from src.multi_agents.state import AgentState

settings = get_settings()
logger = setup_logger("BASE_AGENT")

class BaseAgent(ABC):
    def __init__(self, model_key: str = "orchestrator"):
        cfg = settings.MODELS[model_key]
        self.llm = ChatOllama(
            model=cfg["model_name"],
            temperature=cfg.get("temperature", 0.1),
            num_ctx=cfg.get("context_window", 32768)
        )
        self.searxng_url = settings.search_url
        self.system_prompt = ""
        logger.info(f"Initialized {self.__class__.__name__} with model: {cfg['model_name']}")

    def _get_strict_system_prompt(self, context: str) -> str:
        return (
            f"{self.system_prompt}\n"
            f"CONTEXT FROM DATA SOURCES:\n{context}\n\n"
            "STRICT RULES:\n"
            "- No conversational filler (e.g., 'Sure', 'I found').\n"
            "- No abstractions. Use only provided facts and numbers.\n"
            "- If data is missing, state: 'DATA_NOT_FOUND'.\n"
            "- Format: Concise bullet points or direct values."
        )

    @abstractmethod
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        pass