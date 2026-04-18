from typing import Literal, Optional
from pydantic import BaseModel, Field


class DelegationDecision(BaseModel):
    next_agent: Literal["Scout", "Librarian", "Quant", "Orchestrator", "FINISH"]
    task_description: str = Field(description="Specific task to delegate to the agent")
    reasoning: str = Field(description="Why this agent was chosen")
    needs_replan: bool = Field(default=False, description="Whether to regenerate the plan")


class AgentCapability(BaseModel):
    name: str
    description: str
    best_for: list[str]
    avoid_for: list[str]
