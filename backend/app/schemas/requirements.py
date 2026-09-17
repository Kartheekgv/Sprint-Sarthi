from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RequirementDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=5, max_length=500)
    description: str = Field(min_length=10, max_length=5000)
    category: Literal[
        "functional", "non_functional", "business_rule", "data", "integration",
        "security", "performance", "availability", "scalability", "accessibility",
        "usability", "auditability", "reporting", "operational", "constraint", "assumption",
    ]
    requirement_status: Literal["explicit", "inferred", "candidate"]
    actors: list[str] = Field(default_factory=list, max_length=20)
    systems: list[str] = Field(default_factory=list, max_length=20)
    business_rules: list[str] = Field(default_factory=list, max_length=20)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    priority: Literal["Highest", "High", "Medium", "Low", "Lowest", "Unknown"]
    rationale: str = Field(min_length=5, max_length=2000)
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=10)
    source_references: list[str] = Field(min_length=1, max_length=10)
    confidence: float = Field(ge=0, le=1)
    requires_clarification: bool
    clarification_reasons: list[str] = Field(default_factory=list, max_length=20)


class RequirementBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirements: list[RequirementDraft] = Field(min_length=1, max_length=40)


class RequirementRead(BaseModel):
    id: str
    stable_id: str
    title: str
    description: str
    category: str
    requirement_status: str
    actors: list[str]
    systems: list[str]
    business_rules: list[str]
    constraints: list[str]
    assumptions: list[str]
    priority: str
    rationale: str
    acceptance_criteria: list[str]
    source_references: list[str]
    confidence: float
    requires_clarification: bool
    clarification_reasons: list[str]
    provenance: dict[str, object]
    status: str


class RequirementGenerationResult(BaseModel):
    session_id: str
    session_status: str
    requirements: list[RequirementRead]