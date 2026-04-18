from typing import List, Literal
from pydantic import BaseModel, Field


class Step(BaseModel):
    step_id: int
    task: str = Field(description="Concrete task description.")
    target_agent: Literal["Librarian", "Quant", "Scout"] = Field(
        description="Strict choice from available agents."
    )
    rationale: str = Field(description="Reasoning for agent selection.")


class Plan(BaseModel):
    steps: List[Step] = Field(description="The sequential execution plan.")

    def current_step(self, completed: int = 0) -> Step | None:
        if completed < len(self.steps):
            return self.steps[completed]
        return None

    def is_complete(self, completed: int = 0) -> bool:
        return completed >= len(self.steps)
