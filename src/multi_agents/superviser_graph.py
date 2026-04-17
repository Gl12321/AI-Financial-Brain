from typing import Annotated, TypedDict, List, Union, Literal
from src.multi_agents.state import AgentState
from langgraph.graph import StateGraph, END

from agents.orchestrator import Orchestrator
from agents.librarian import Librarian
from agents.quant import Quant
from agents.scout import Scout
from agents.summarizer import SummarizerAgent


class FinancialMultiAgentGraph:
    def __init__(self, llm):
        self.orchestrator = Orchestrator()
        self.librarian = Librarian()
        self.quant = Quant()
        self.scout = Scout()
        self.summarizer = SummarizerAgent()
        self.max_iterations = 10

    async def _summarizer_node(self, state: AgentState):
        return await self.summarizer.execute(state)

    async def _manager_node(self, state: AgentState):
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        return await self.orchestrator.execute(state)

    async def _librarian_node(self, state: AgentState):
        return await self.librarian.execute(state)

    async def _quant_node(self, state: AgentState):
        return await self.quant.execute(state)

    async def _scout_node(self, state: AgentState):
        return await self.scout.execute(state)

    def _router(self, state: AgentState) -> Literal["librarian", "quant", "scout", "end"]:
        if state["iteration_count"] >= self.max_iterations:
            return "end"

        next_actor = state.get("next_actor", "FINISH").upper()

        if next_actor == "LIBRARIAN":
            return "librarian"
        elif next_actor == "QUANT":
            return "quant"
        elif next_actor == "SCOUT":
            return "scout"
        else:
            return "end"

    def build(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("summarizer", self._summarizer_node)
        workflow.add_node("manager", self._manager_node)
        workflow.add_node("librarian", self._librarian_node)
        workflow.add_node("quant", self._quant_node)
        workflow.add_node("scout", self._scout_node)

        workflow.set_entry_point("summarizer")

        workflow.add_edge("summarizer", "manager")
        workflow.add_edge("librarian", "manager")
        workflow.add_edge("quant", "manager")
        workflow.add_edge("scout", "manager")

        workflow.add_conditional_edges(
            "manager",
            self._router,
            {
                "librarian": "librarian",
                "quant": "quant",
                "scout": "scout",
                "end": END
            }
        )

        return workflow.compile()