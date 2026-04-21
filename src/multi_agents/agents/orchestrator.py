import json
from typing import Dict, Any
from pydantic import ValidationError
from langchain_core.messages import SystemMessage, HumanMessage

from src.multi_agents.agents.base import BaseAgent
from src.multi_agents.state import AgentState
from src.multi_agents.schemas.models import AgentCapability, DelegationDecision
from src.multi_agents.schemas.types import Plan, Step
from src.core.logger import setup_logger

logger = setup_logger("ORCHESTRATOR")

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.max_retries = 3
        self.available_agents = ["Scout", "Librarian", "Quant"]
        self._agent_capabilities = {
            "Librarian": AgentCapability(
                name="Librarian",
                description="GraphRAG retrieval from EDGAR 2023 filings of american companies. Historical data, corporate structure, risk factors, MD&A, information of investments",
                best_for=["historical financials", "10-K analysis", "corporate structure", "risk factors",
                          "EDGAR data"],
                avoid_for=["real-time news", "post-2023 data", "market predictions"]
            ),
            "Scout": AgentCapability(
                name="Scout",
                description="Web search and news aggregation. Current market sentiment, breaking news",
                best_for=["news search", "current events", "market sentiment"],
                avoid_for = ["historical deep-dive", "structured filings", "mathematical modeling"]
            ),
            "Quant": AgentCapability(
                name="Quant",
                description="Mathematical modeling and ML forecasting. Profit prediction for any company from EDGAR 2023 filings",
                best_for=["profit forecasting", "financial modeling", "trend extrapolation", "2024 predictions"],
                avoid_for=["qualitative analysis", "news interpretation", "one-time events"]
            )
        }
        self.capabilities_text = "\n".join([
            f"""
            - {name}: {cap.description}\n Best for: {', '.join(cap.best_for)} \n
            Strictly avoid: {', '.join(cap.avoid_for)}
            """
            for name, cap in self._agent_capabilities.items()
        ])


    async def _generate_plan(self, query: str, summary: str) -> Plan:
        system_prompt = (
            "You are a Financial Task Architect. Create an optimal execution plan.\n\n"
            f"AVAILABLE AGENTS:\n{self.capabilities_text}\n\n"
            "PLANNING RULES:\n"
            "1. Break complex queries into sequential steps\n"
            "2. Librarian first for historical context, then Quant for forecasting, Scout for current data\n"
            "3. Each step must have concrete, actionable task description\n"
            "4. Use minimal steps needed - avoid over-delegation\n"
            "5. For simple queries, use single-agent plans\n\n"
            "OUTPUT: JSON with 'steps' array. Each step: step_id, task, target_agent (Librarian/Quant/Scout), rationale"
        )

        user_prompt = (
            f"CONVERSATION CONTEXT: {summary if summary else 'No context available'}\n\n"
            f"USER QUERY: {query} \n\n"
            f"Create execution plan:"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        for attempt in range(self.max_retries):
            try:
                response = await self.llm.ainvoke(messages)
                data = json.loads(response.content)
                return Plan(**data)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Plan generation attempt {attempt + 1}/{self.max_retries} failed: {e}")

                if attempt < self.max_retries - 1:
                    messages.append(HumanMessage(
                        content=f"""
                            Your previous response was invalid: {str(e)[:200]}. 
                            Please return a valid JSON matching the Plan schema with 'steps' array
                            """
                        )
                    )
                else:
                    logger.error(f"All retries failed, using fallback plan")
                    raise Exception("Failed to generate plan after multiple attempts")

    async def _route_task(self, current_step: Step) -> DelegationDecision:
        return DelegationDecision(
            next_agent=current_step.target_agent,
            task_description=current_step.task,
            reasoning=f"Following plan step {current_step.step_id}: {current_step.rationale}",
            needs_replan=False
        )

    async def _synthesize_final_answer(self, state: AgentState) -> str:
        agent_outcomes = state.get("agent_outcomes", [])
        query = state.get("user_query", "")

        system_prompt = (
            "You are a Senior Financial Analyst synthesizing multi-source research.\n\n"
            "SYNTHESIS RULES:\n"
            "1. Lead with direct answer to the query\n"
            "2. Cite sources: [Librarian], [Quant], [Scout]\n"
            "3. Highlight conflicts between sources if any\n"
            "4. Distinguish facts vs forecasts vs real-time data\n"
            "5. No filler phrases (As an AI, It is important to note)\n"
            "6. Professional financial report tone\n\n"
            "STRUCTURE:\n"
            "- Executive Summary (2-3 sentences)\n"
            "- Detailed Analysis (bullet points with data)\n"
            "- Sources & Methodology"
        )

        user_prompt = (
            f"ORIGINAL QUERY: {query}\n\n"
            f"RAW AGENTS OUTPUTS:\n{agent_outcomes}\n\n"
            "Synthesize final report:"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Final synthesis failed: {e}")
            return self._create_basic_summary(query, agent_outcomes)

    def _create_basic_summary(self, query: str, outcomes: List[str]) -> str:
        summary = f"## Analysis: {query[:80]}\n\n"
        summary += "### Agent Contributions:\n"

        summary += "\n".join(outcomes[-10:])

        return summary

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        user_query = state.get("user_query", "")
        summary = state.get("conversation_summary", "")
        completed_steps = state.get("completed_steps", 0)

        if not state.get("plan"):
            logger.info(f"Orchestrator processing: {user_query[:60]}")
            plan = await self._generate_plan(user_query, summary)
            state["agent_outcomes"] = state.get("agent_outcomes", []) + [
                f"Plan created: {len(plan.steps)} steps"
            ]
            logger.info(f"Orchestrator: Generated plan with {len(plan.steps)} steps")
            return {
                "status": "RUNNING",
                "next_agent": "Orchestrator",
                "current_task": "Plan generated, ready to execute",
                "iteration_count": 0,
                "plan": plan.model_dump()
            }

        plan = Plan(**state["plan"])
        current_step = plan.current_step(completed_steps)
        
        if current_step is None or plan.is_complete(completed_steps):
            logger.info("Plan complete - synthesizing final answer")
            final_answer = await self._synthesize_final_answer(state)
            return {
                "status": "FINISH",
                "final_answer": final_answer,
                "current_task": "Complete"
            }
        
        decision = await self._route_task(current_step)

        if decision.next_agent == "FINISH":
            logger.info("Early finish detected")
            final_answer = await self._synthesize_final_answer(state)
            return {
                "status": "FINISH",
                "final_answer": final_answer,
                "current_task": "Complete"
            }

        logger.info(f"Delegating to {decision.next_agent}: {decision.task_description[:50]}...")

        return {
            "status": "RUNNING",
            "next_agent": decision.next_agent,
            "current_task": decision.task_description,
            "agent_outcomes": state.get("agent_outcomes", []) + [
                f"Orchestrator → {decision.next_agent}: {decision.reasoning}"
            ],
            "iteration_count": state.get("iteration_count", 0) + 1
        }
