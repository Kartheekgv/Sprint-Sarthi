import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Document, DocumentSection, Epic, Requirement, Task, UserStory
from app.schemas.evidence import SourceEvidenceRead


BacklogModel = type[Requirement] | type[Epic] | type[UserStory] | type[Task]
MODEL_BY_TYPE: dict[str, BacklogModel] = {
    "requirement": Requirement,
    "epic": Epic,
    "story": UserStory,
    "task": Task,
}


@dataclass(frozen=True)
class EvidenceResolution:
    sources: list[SourceEvidenceRead]
    unresolved_references: list[str]


def source_reference(document_name: str, heading: str, page: int | None) -> str:
    return f"{document_name} | {heading}" + (f" | page {page}" if page else "")


def bounded_snippet(content: str, limit: int = 700) -> str:
    normalized = " ".join(content.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit].rstrip()}..."


async def resolve_item_evidence(
    db: AsyncSession,
    item_type: Literal["requirement", "epic", "story", "task"],
    item_id: str,
) -> EvidenceResolution | None:
    model = MODEL_BY_TYPE[item_type]
    item = await db.get(model, item_id)
    if item is None:
        return None
    references = json.loads(item.source_references_json)
    rows = (await db.execute(
        select(DocumentSection, Document.original_name)
        .join(Document, Document.id == DocumentSection.document_id)
        .where(Document.project_id == item.project_id)
        .order_by(Document.original_name, DocumentSection.page, DocumentSection.chunk_index)
    )).all()
    sources: list[SourceEvidenceRead] = []
    resolved: set[str] = set()
    for section, document_name in rows:
        reference = source_reference(document_name, section.heading, section.page)
        if reference not in references:
            continue
        resolved.add(reference)
        sources.append(SourceEvidenceRead(
            section_id=section.id,
            document_id=section.document_id,
            document_name=document_name,
            section=section.section,
            heading=section.heading,
            page=section.page,
            chunk_index=section.chunk_index,
            snippet=bounded_snippet(section.content),
            reference=reference,
        ))
    return EvidenceResolution(sources, [reference for reference in references if reference not in resolved])