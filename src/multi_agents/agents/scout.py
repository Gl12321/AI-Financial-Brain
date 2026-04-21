import httpx
from typing import Dict, Any

from .base import BaseAgent
from src.core.config import get_settings
from src.core.logger import setup_logger

settings = get_settings()
logger = setup_logger("SCOUT")



class Scout(BaseAgent):
    def __init__(self):
        super().__init__()

    async def _local_search(self, query: str) -> str:
        params = {
            "q": query,
            "format": "json",
            "categories": "general"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self.searxng_url, params=params)
            results = response.json().get("results", [])
            return "\n".join([f"{r['title']}: {r['content']}" for r in results[:5]])

    async def _summarize(self, text: str) -> str:
        prompt = f"Summarize the following text: {text}"
        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        return response.content

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        task = state.get("current_task", state.get("current_step_task"))
        logger.info(f"Searching for: {task[:50]}..." if task else "No task provided")

        raw_web_data = await self._local_search(task)
        summarized_raw_web_data = await self._summarize(raw_web_data)
        logger.info(f"Retrieved {len(raw_web_data)} chars from web search")

        prompt = f"Analyze these local search results and extract facts about {task}. Results: {raw_web_data}"
        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])

        logger.info("Web search analysis complete")

        return {
            "context": [f"LOCAL_WEB_SOURCE: {response.content}"],
            "last_actor": "Scout"
        }