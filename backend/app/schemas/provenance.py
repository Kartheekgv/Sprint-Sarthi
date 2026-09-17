from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(pattern=r"^DOC-\d{3,}$")
    file_name: str = Field(min_length=1, max_length=255)
    page_number: int | None = Field(default=None, ge=1)
    section_heading: str | None = Field(default=None, max_length=500)
    chunk_id: str = Field(pattern=r"^CHUNK-\d{3,}$")
    quoted_text: str = Field(min_length=1, max_length=700)


ValueType = TypeVar("ValueType")


class ProvenanceValue(BaseModel, Generic[ValueType]):
    model_config = ConfigDict(extra="forbid")
    value: ValueType
    origin: Literal["extracted", "inferred", "calculated", "human_provided"]
    confidence: float = Field(ge=0, le=1)
    source_references: list[SourceReference] = Field(default_factory=list, max_length=20)
    requires_review: bool = False

    @model_validator(mode="after")
    def unsupported_values_require_review(self):
        if self.origin == "extracted" and not self.source_references:
            raise ValueError("extracted values require at least one source reference")
        if not self.source_references and self.origin in {"inferred", "calculated"} and not self.requires_review:
            raise ValueError("unsupported inferred or calculated values must require review")
        return self