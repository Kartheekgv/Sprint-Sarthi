from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str
    status: str
    created_at: datetime


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    document_code: str
    project_id: str
    original_name: str
    media_type: str
    size_bytes: int
    sha256: str
    status: str
    created_at: datetime


class DocumentChunkRead(BaseModel):
    id: str
    chunk_id: str
    document_id: str
    file_name: str
    page_number: int | None
    section_heading: str
    content: str
    token_count: int
    metadata: dict[str, object]
    extraction_confidence: float


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    kind: str
    status: str
    progress: int
    error: str | None
    created_at: datetime
