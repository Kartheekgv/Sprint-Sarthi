from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApprovalDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject", "request_changes"]
    approved_by: str = Field(min_length=2, max_length=200)
    note: str = Field(default="", max_length=5000)


class ApprovalDecisionRead(BaseModel):
    id: str
    session_id: str
    decision: str
    approved_by: str
    note: str
    session_status: str


class ExportRead(BaseModel):
    id: str
    session_id: str
    filename: str
    sha256: str
    status: str
    download_url: str