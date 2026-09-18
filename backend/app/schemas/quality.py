from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QualityClarificationAnswerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: dict[str, str | int | float | list[str]] = Field(min_length=1)


class QualityClarificationRead(BaseModel):
    id: str
    session_id: str
    item_id: str
    item_type: Literal["epic", "feature", "story", "task"]
    missing_fields: list[str]
    question: str
    answer: dict[str, object]
    status: str
    created_at: datetime


class QualityRead(BaseModel):
    id: str
    item_id: str
    item_type: str
    score: int
    passed: bool
    issues: list[str]
    checks: dict[str, bool]


class QualityGenerationResult(BaseModel):
    session_id: str
    session_status: str
    results: list[QualityRead]
    clarifications: list[QualityClarificationRead] = []


class BoardHealthRead(BaseModel):
    id: str
    score: int
    risk_level: str
    metrics: dict[str, int | float]
    issues: list[str]
    status: str


class BoardHealthGenerationResult(BaseModel):
    session_id: str
    session_status: str
    health: BoardHealthRead