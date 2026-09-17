from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DuplicateDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_stable_id: str = Field(pattern=r"^(EPIC|STORY|TASK)-\d{3,}$")
    target_stable_id: str = Field(pattern=r"^(EPIC|STORY|TASK)-\d{3,}$")
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