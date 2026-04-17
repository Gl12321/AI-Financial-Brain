from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from abc import ABC, abstractmethod

from src.core.config import get_settings
from src.multi_agents.state import AgentState

settings = get_settings()

class BaseAgent(ABC):
    def __init__(self):
        self.llm = ChatOllama(model=settings.MODELS["orchestrator"]["model_name"])
        self.searxng_url = settings.search_url
        self.system_prompt = ""

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