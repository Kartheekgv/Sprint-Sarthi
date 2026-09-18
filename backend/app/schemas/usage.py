from datetime import datetime
from typing import Any

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


class LogProjectRead(BaseModel):
    id: str
    name: str


class OperationalLogRead(BaseModel):
    id: str
    kind: str
    created_at: datetime
    project_id: str | None
    project_name: str
    session_id: str | None
    source: str
    status: str
    message: str
    metadata: dict[str, Any]


class OperationalLogsRead(BaseModel):
    entries: list[OperationalLogRead]
    projects: list[LogProjectRead]