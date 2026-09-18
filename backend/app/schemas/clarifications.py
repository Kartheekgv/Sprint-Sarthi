from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClarificationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement_id: str = Field(pattern=r"^REQ-\d{3,}$")
    question: str = Field(min_length=5, max_length=1000)
    reason: str = Field(min_length=5, max_length=2000)
    severity: Literal["critical", "high", "medium", "low"]
    missing_field: str = Field(min_length=1, max_length=100)
    recommended_answer_type: Literal["single_select", "multi_select", "text", "number", "date", "boolean"]
    options: list[str] = Field(min_length=3, max_length=5)
    recommended_option: str
    allow_custom_answer: bool
    blocking: bool
    source_references: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def recommendation_is_an_option(self):
        if self.recommended_option not in self.options:
            raise ValueError("recommended_option must exactly match one option")
        if len(set(self.options)) != len(self.options):
            raise ValueError("options must be unique")
        if self.severity == "critical" and not self.blocking:
            raise ValueError("critical clarifications must be blocking")
        return self


class ClarificationBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[ClarificationDraft] = Field(min_length=1, max_length=8)


class ClarificationOptionRead(BaseModel):
    id: str
    label: str
    position: int


class ClarificationRead(BaseModel):
    id: str
    session_id: str
    requirement_id: str
    question: str
    reason: str
    severity: str
    missing_field: str
    recommended_answer_type: str
    blocking: bool
    required: bool
    recommended_option_id: str
    allow_custom_answer: bool
    source_references: list[str]
    options: list[ClarificationOptionRead]


class AnalysisSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    thread_id: str
    status: str
    current_node: str | None
    created_at: datetime


class ClarificationAnswerCreate(BaseModel):
    action: Literal["selected", "default", "custom", "skip", "unknown"]
    option_id: str | None = None
    custom_answer: str | None = Field(default=None, max_length=4000)


class ClarificationAnswerResult(BaseModel):
    session_id: str
    session_status: str
    has_next: bool


class ClarificationHistoryRead(BaseModel):
    id: str
    requirement_id: str
    question: str
    severity: str
    status: str
    action: str | None
    answer: str | None
    answered_at: datetime | None


class AgentPromptCreate(BaseModel):
    message: str = Field(min_length=2, max_length=4000)


class AgentFeedbackDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    understanding: str = Field(min_length=2, max_length=2000)
    affected_artifacts: list[str] = Field(max_length=20)
    needs_clarification: list[str] = Field(max_length=20)
    revision_plan: list[str] = Field(min_length=1, max_length=20)


class AgentMessageRead(BaseModel):
    id: str
    agent_name: str
    role: Literal["human", "assistant"]
    content: str
    created_at: datetime


class AgentPromptResult(BaseModel):
    agent_name: str
    response: str
    mutation_applied: bool = False