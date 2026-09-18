from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SprintDecisionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    story_stable_id: str = Field(pattern=r"^STORY-\d{3,}$")
    decision: Literal["planned", "deferred"]
    sprint_id: str | None = None
    assignee_id: str | None = None
    reason: str = Field(min_length=10, max_length=2000)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_decision_fields(self) -> "SprintDecisionDraft":
        if self.decision == "planned" and (not self.sprint_id or not self.assignee_id):
            raise ValueError("Planned stories require sprint_id and assignee_id")
        if self.decision == "deferred" and self.sprint_id is not None:
            raise ValueError("Deferred stories cannot reference a sprint")
        return self


class SprintPlanningBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[SprintDecisionDraft] = Field(min_length=1, max_length=100)


class SprintDecisionRead(BaseModel):
    id: str
    story_stable_id: str
    story_title: str
    story_points: int
    decision: str
    sprint_id: str | None
    sprint_name: str | None
    assignee_id: str | None
    assignee_name: str | None
    reason: str
    confidence: float
    provenance: dict[str, object]
    status: str


class SprintPlanningResult(BaseModel):
    session_id: str
    session_status: str
    decisions: list[SprintDecisionRead]
    ordering_heuristic: str
    forecast_completion_date: date | None
    total_planned_points: int
    total_available_capacity_points: float


class SprintScopeReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewed_by: str = Field(min_length=2, max_length=200)
    selected_task_ids: list[str] = Field(min_length=1, max_length=300)
    note: str = Field(default="", max_length=4000)


class SprintScopeTaskRead(BaseModel):
    stable_id: str
    story_stable_id: str
    title: str
    work_category: str
    estimated_hours: float | None
    selected: bool


class SprintScopeStoryRead(BaseModel):
    stable_id: str
    title: str
    story_points: int
    priority: str
    selected: bool
    tasks: list[SprintScopeTaskRead]


class SprintScopeReviewRead(BaseModel):
    id: str | None
    session_id: str
    reviewed_by: str
    selected_task_ids: list[str]
    discarded_task_ids: list[str]
    selected_story_ids: list[str]
    note: str
    reviewed: bool
    stories: list[SprintScopeStoryRead]