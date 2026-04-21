from typing import Dict, Any
from .base import BaseAgent
from src.core.logger import setup_logger

logger = setup_logger("SUMMARIZER")


class SummarizerAgent(BaseAgent):
    def __init__(self):
        super().__init__()

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        full_context = state.get("context", [])
        context_len = len(str(full_context))

        if context_len < 4000:
            logger.info(f"Context length {context_len} bytes, skipping compression")
            return {
                "agent_outcomes": ["Summarizer: Context length is optimal, skipping."]
            }

        logger.info(f"Compressing context ({context_len} bytes)")

        prompt = f"""
        STRICT FINANCIAL SUMMARIZATION:
        Extract only hard facts, tickers, and financial metrics from the provided text.
        Delete all conversational filler, greetings, and duplicated info.

        INPUT CONTEXT:
        {full_context}
        """

        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        logger.info("Context compression complete")

        return {
            "context": [f"CONSOLIDATED_FINANCIAL_DATA: {response.content}"],
            "agent_outcomes": ["Summarizer: Context compressed for optimization."]
        }