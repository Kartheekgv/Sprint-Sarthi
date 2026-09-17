from datetime import datetime

from pydantic import BaseModel


class AgentUsageRead(BaseModel):
    node_name: str
    model: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    remaining_tokens: int | None
    duration_ms: int | None
    created_at: datetime


class SessionUsageRead(BaseModel):
    session_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    remaining_tokens: int | None
    remaining_reported: bool
    executions: list[AgentUsageRead]