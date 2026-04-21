from typing import Annotated, TypedDict, List, Union, Literal
from src.multi_agents.state import AgentState
from src.core.logger import setup_logger
from langgraph.graph import StateGraph, END

from src.multi_agents.agents.orchestrator import OrchestratorAgent
from src.multi_agents.agents.librarian import Librarian
from src.multi_agents.agents.quant import Quant
from src.multi_agents.agents.scout import Scout
from src.multi_agents.agents.summarizer import SummarizerAgent

logger = setup_logger("SUPERVISER_GRAPH")

class FinancialMultiAgentGraph:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.librarian = Librarian()
        self.quant = Quant()
        self.scout = Scout()
        self.summarizer = SummarizerAgent()
        self.max_iterations = 10
        logger.info("Graph initialized")

    async def _summarizer_node(self, state: AgentState):
        logger.debug("Running summarizer node")
        return await self.summarizer.execute(state)

    async def _manager_node(self, state: AgentState):
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        state["completed_steps"] = state.get("completed_steps", 0)
        logger.debug(f"Running manager node, iteration {state['iteration_count']}")
        return await self.orchestrator.execute(state)

    async def _librarian_node(self, state: AgentState):
        result = await self.librarian.execute(state)
        return {
            **result,
            "completed_steps": state.get("completed_steps", 0) + 1
        }

    async def _quant_node(self, state: AgentState):
        result = await self.quant.execute(state)
        return {
            **result,
            "completed_steps": state.get("completed_steps", 0) + 1
        }

    async def _scout_node(self, state: AgentState):
        logger.debug("Running scout node")
        result = await self.scout.execute(state)
        return {
            **result,
            "completed_steps": state.get("completed_steps", 0) + 1
        }

    def _router(self, state: AgentState) -> Literal["librarian", "quant", "scout", "end"]:
        if state["iteration_count"] >= self.max_iterations:
            logger.warning(f"Max iterations ({self.max_iterations}) reached")
            return "end"

        next_actor = state.get("next_actor", "FINISH").upper()
        logger.debug(f"Routing to: {next_actor}")

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

        logger.info("Workflow compiled")
        return workflow.compile()