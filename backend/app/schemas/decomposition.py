from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DecompositionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement_ids: list[str] = Field(min_length=1, max_length=20)
    parent_capability: str = Field(min_length=3, max_length=300)
    component_type: Literal["business_capability", "feature", "workflow", "technical_component"]
    title: str = Field(min_length=5, max_length=500)
    description: str = Field(min_length=10, max_length=5000)
    suggested_backlog_level: Literal["epic", "story", "task"]
    rationale: str = Field(min_length=5, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class DecompositionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decompositions: list[DecompositionDraft] = Field(min_length=1, max_length=100)


class DecompositionRead(BaseModel):
    id: str
    stable_id: str
    requirement_ids: list[str]
    parent_capability: str
    component_type: str
    title: str
    description: str
    suggested_backlog_level: str
    rationale: str
    source_references: list[str]
    confidence: float
    provenance: dict[str, object]
    status: str


class DecompositionGenerationResult(BaseModel):
    session_id: str
    session_status: str
    decompositions: list[DecompositionRead]