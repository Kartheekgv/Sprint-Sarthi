from typing import Literal

from pydantic import BaseModel, Field


BacklogItemType = Literal["requirement", "epic", "story", "task"]


class SourceEvidenceRead(BaseModel):
    section_id: str
    document_id: str
    document_name: str
    section: str
    heading: str
    page: int | None
    chunk_index: int
    snippet: str
    reference: str


class BacklogSourcesRead(BaseModel):
    item_id: str
    item_type: BacklogItemType
    sources: list[SourceEvidenceRead]
    unresolved_references: list[str] = Field(default_factory=list)