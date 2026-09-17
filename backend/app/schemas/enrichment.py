from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Priority = Literal["Critical", "High", "Medium", "Low"]


class EpicEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stable_id: str = Field(pattern=r"^EPIC-\d{3,}$")
    business_value: str = Field(min_length=10, max_length=2000)
    priority: Priority
    acceptance_criteria: list[str] = Field(min_length=1, max_length=20)
    confidence: float = Field(ge=0, le=1)


class StoryEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stable_id: str = Field(pattern=r"^STORY-\d{3,}$")
    acceptance_criteria: list[str] = Field(min_length=1, max_length=20)
    priority: Priority
    confidence: float = Field(ge=0, le=1)


class TaskEnrichment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stable_id: str = Field(pattern=r"^TASK-\d{3,}$")
    priority: Priority
    confidence: float = Field(ge=0, le=1)


class EnrichmentBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epics: list[EpicEnrichment] = Field(min_length=1, max_length=30)
    stories: list[StoryEnrichment] = Field(min_length=1, max_length=100)
    tasks: list[TaskEnrichment] = Field(min_length=1, max_length=300)