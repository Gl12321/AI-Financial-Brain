from typing import Annotated, TypedDict, List, Union, Literal
import operator


class AgentState(TypedDict):

    original_task: str
    current_step_task: str
    plan: List[str]
    context: Annotated[List[str], operator.add]
    agent_outcomes: Annotated[List[str], operator.add]
    next_actor: str
    final_report: str
    iteration_count: int

