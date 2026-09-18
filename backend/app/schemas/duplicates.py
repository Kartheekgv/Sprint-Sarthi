from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DuplicateDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_stable_id: str = Field(pattern=r"^(EPIC|FEATURE|STORY|TASK)-\d{3,}$")
    target_stable_id: str = Field(pattern=r"^(EPIC|FEATURE|STORY|TASK)-\d{3,}$")
    similarity: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=10, max_length=2000)
    recommendation: Literal["merge", "keep_both", "clarify"]
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="before")
    @classmethod
    def normalize_pair_order(cls, value: object) -> object:
        if isinstance(value, dict):
            source = value.get("source_stable_id")
            target = value.get("target_stable_id")
            if isinstance(source, str) and isinstance(target, str) and source > target:
                return {**value, "source_stable_id": target, "target_stable_id": source}
        return value

    @model_validator(mode="after")
    def canonical_pair(self) -> "DuplicateDraft":
        if self.source_stable_id == self.target_stable_id:
            raise ValueError("Duplicate pairs cannot self-reference")
        return self


class DuplicateBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidates: list[DuplicateDraft] = Field(max_length=300)


class DuplicateRead(BaseModel):
    id: str
    source_stable_id: str
    target_stable_id: str
    similarity: float
    rationale: str
    recommendation: str
    confidence: float
    provenance: dict[str, object]
    status: str


class DuplicateGenerationResult(BaseModel):
    session_id: str
    session_status: str
    candidates: list[DuplicateRead]


class NewStoryCheckCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=5, max_length=500)
    user_story: str = Field(min_length=10, max_length=2000)
    description: str = Field(min_length=10, max_length=5000)
    priority: Literal["Critical", "High", "Medium", "Low"]
    story_points: Literal[1, 2, 3, 5, 8, 13]
    acceptance_criteria: list[str] = Field(min_length=1, max_length=12)
    definition_of_done: list[str] = Field(min_length=1, max_length=12)
    source_references: list[str] = Field(min_length=1, max_length=10)


class NewStoryAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    classification: Literal["duplicate", "new", "clarification"]
    equivalent_story_id: str | None = None
    suggested_feature_id: str | None = None
    suggested_sprint_id: str | None = None
    rationale: str = Field(min_length=10, max_length=2000)
    clarifying_questions: list[str] = Field(max_length=8)
    confidence: float = Field(ge=0, le=1)


class NewStoryCheckRead(NewStoryAssessment):
    id: str
    session_id: str
    proposal: NewStoryCheckCreate
    status: str


class NewStoryConfirmCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_id: str
    confirmed: Literal[True]


class NewStoryCreateResult(BaseModel):
    check_id: str
    story_id: str
    story_stable_id: str
    suggested_sprint_id: str | None
    sprint_mutation_applied: bool = False