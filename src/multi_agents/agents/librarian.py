import json
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage

from .base import BaseAgent
from src.rag.retriever import Retriever, TraversalStrategy
from src.core.config import get_settings
from src.core.logger import setup_logger

settings = get_settings()
logger = setup_logger("LIBRARIAN")


class Librarian(BaseAgent):
    def __init__(self):
        super().__init__()
        self._retriever = Retriever()

    def _select_strategy(self, task: str, company_cik: int = None) -> TraversalStrategy:
        task_lower = task.lower()
        
        if company_cik and any(kw in task_lower for kw in ["investor", "institutional", "ownership", "manager"]):
            logger.info("Selected INVESTMENT_GRAPH strategy")
            return TraversalStrategy.INVESTMENT_GRAPH
        
        if any(kw in task_lower for kw in ["risk", "business model", "operations", "md&a"]):
            logger.info("Selected SECTION_FOCUSED strategy (Item 1, 1a, 7)")
            return TraversalStrategy.SECTION_FOCUSED
        
        if company_cik:
            logger.info("Selected COMPANY_FORMS strategy")
            return TraversalStrategy.COMPANY_FORMS
        
        logger.info("Selected HYBRID strategy")
        return TraversalStrategy.HYBRID

    def _get_section_items(self, task: str) -> List[str]:
        task_lower = task.lower()
        sections = []
        
        if any(kw in task_lower for kw in ["risk", "risk factor", "uncertainty"]):
            sections.append("item1a")
        if any(kw in task_lower for kw in ["business", "operations", "model", "strategy"]):
            sections.append("item1")
        if any(kw in task_lower for kw in ["md&a", "discussion", "analysis", "management"]):
            sections.append("item7")
        if any(kw in task_lower for kw in ["market risk", "quantitative", "disclosure"]):
            sections.append("item7a")
        
        return sections if sections else ["item7", "item1", "item1a"]

    async def _retrieve_documents(
        self,
        task: str,
        company_cik: int = None
    ) -> Dict[str, Any]:
        strategy = self._select_strategy(task, company_cik)
        section_items = None
        
        if strategy == TraversalStrategy.SECTION_FOCUSED:
            section_items = self._get_section_items(task)
        
        result = await self._retriever.retrieve(
            query=task,
            strategy=strategy,
            company_cik=company_cik,
            section_items=section_items,
            top_k=5
        )
        
        return result

    async def _synthesize_strict_answer(
        self,
        task: str,
        retrieved_data: Dict[str, Any]
    ) -> str:
        chunks = retrieved_data.get("chunks", [])
        strategy = retrieved_data.get("strategy", "unknown")
        
        if not chunks:
            return "DATA_NOT_FOUND: No relevant EDGAR documents retrieved."
        
        context_text = "\n\n".join([
            f"[Source: chunk_{c['chunk_id']}, item: {c.get('item', 'unknown')}, score: {c['score']:.3f}]\n{c['text'][:800]}"
            for c in chunks[:3]
        ])
        
        system_prompt = (
            "You are a Financial Data Librarian. Extract ONLY hard facts from EDGAR filings. "
            "No analysis, no opinions, no filler phrases.\n\n"
            "OUTPUT RULES:\n"
            "- Bullet points only\n"
            "- Include specific numbers, dates, percentages\n"
            "- Cite source: [chunk_id, item]\n"
            "- If information missing, state: NOT_FOUND"
        )
        
        user_prompt = (
            f"TASK: {task}\n"
            f"RETRIEVAL STRATEGY: {strategy}\n"
            f"DOCUMENTS FOUND: {len(chunks)}\n\n"
            f"RAW DOCUMENTS:\n{context_text}\n\n"
            "Extract strict facts:"
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        task = state.get("current_task", "")
        company_cik = state.get("company_cik")

        logger.info(f"Librarian processing: {task[:60]}...")

        retrieved = await self._retrieve_documents(task, company_cik)
        logger.info(f"Retrieved {retrieved.get('total', 0)} chunks via {retrieved.get('strategy')}")

        strict_answer = await self._synthesize_strict_answer(task, retrieved)
        logger.info(f"Synthesized answer: {len(strict_answer)} chars")

        return {
            "context": [f"LIBRARIAN_SOURCE: {strict_answer}"],
            "retrieved_chunks": retrieved.get("chunks", []),
            "retrieval_strategy": retrieved.get("strategy"),
            "company_cik": company_cik,
            "last_actor": "Librarian"
        }
