from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EstimationBriefCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answered_by: str = Field(min_length=2, max_length=200)
    ranked_epic_ids: list[str] = Field(min_length=1, max_length=30)
    priority_rationale: str = Field(min_length=10, max_length=4000)


class EstimationBriefRead(EstimationBriefCreate):
    id: str
    session_id: str
    created_at: datetime
    updated_at: datetime


class EstimationEpicOption(BaseModel):
    stable_id: str
    title: str
    business_value: str
    architecture_layer: str
    current_priority: str


class EstimationBriefWorkspace(BaseModel):
    brief: EstimationBriefRead | None
    epics: list[EstimationEpicOption]
    parallel_groups: list[list[str]]
    parallelism_note: str


class StoryEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stable_id: str = Field(pattern=r"^STORY-\d{3,}$")
    story_points: Literal[1, 2, 3, 5, 8, 13]
    rationale: str = Field(min_length=10, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class TaskEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stable_id: str = Field(pattern=r"^TASK-\d{3,}$")
    estimated_hours: float = Field(gt=0, le=200)
    rationale: str = Field(min_length=10, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class EstimationBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stories: list[StoryEstimate] = Field(min_length=1, max_length=300)
    tasks: list[TaskEstimate] = Field(min_length=1, max_length=1000)