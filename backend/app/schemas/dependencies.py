from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DependencyDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_stable_id: str = Field(pattern=r"^(EPIC|STORY|TASK)-\d{3,}$")
    target_stable_id: str = Field(pattern=r"^(EPIC|STORY|TASK)-\d{3,}$")
    dependency_type: Literal["blocks", "requires", "precedes", "relates_to"]
    risk: Literal["critical", "high", "medium", "low"]
    explanation: str = Field(min_length=10, max_length=2000)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def reject_self_dependency(self) -> "DependencyDraft":
        if self.source_stable_id == self.target_stable_id:
            raise ValueError("A backlog item cannot depend on itself")
        return self


class DependencyBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dependencies: list[DependencyDraft] = Field(max_length=500)

    @model_validator(mode="after")
    def reject_duplicate_edges(self) -> "DependencyBatch":
        edges = [(item.source_stable_id, item.target_stable_id) for item in self.dependencies]
        if len(edges) != len(set(edges)):
            raise ValueError("Dependency edges must be unique")
        return self


class DependencyRead(BaseModel):
    id: str
    source_stable_id: str
    target_stable_id: str
    dependency_type: str
    risk: str
    explanation: str
    confidence: float
    provenance: dict[str, object]


class DependencyGenerationResult(BaseModel):
    session_id: str
    session_status: str
    dependencies: list[DependencyRead]