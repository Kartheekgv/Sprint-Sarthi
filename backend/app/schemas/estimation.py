from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    stories: list[StoryEstimate] = Field(min_length=1, max_length=100)
    tasks: list[TaskEstimate] = Field(min_length=1, max_length=300)