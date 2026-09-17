import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Dependency, Epic, Task, UserStory
from app.providers.base import LLMProvider
from app.schemas.dependencies import DependencyBatch
from app.schemas.provenance import ProvenanceValue, SourceReference


SYSTEM_PROMPT = """You are Sprint Sarthi's Dependency Agent. Return JSON only and never markdown.
Identify only evidence-supported dependencies among supplied backlog items. The source item depends on or is constrained by the target item. Prefer requires, precedes, or blocks; use relates_to only for a meaningful non-sequencing relationship. Return an empty list when no dependency is justified. Do not invent IDs, add scope, estimate, assign people, or schedule work. Never create cycles."""


@dataclass(frozen=True)
class DependencyGeneration:
    batch: DependencyBatch
    prompt_hash: str


def _has_cycle(edges: list[tuple[str, str]]) -> bool:
    graph: dict[str, list[str]] = {}
    for source, target in edges:
        graph.setdefault(source, []).append(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(target) for target in graph.get(node, [])):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


async def generate_dependencies(
    db: AsyncSession,
    session_id: str,
    provider: LLMProvider,
) -> DependencyGeneration:
    epics = (await db.execute(select(Epic).where(Epic.session_id == session_id).order_by(Epic.stable_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id).order_by(Task.stable_id))).scalars().all()
    items = [*epics, *stories, *tasks]
    if not items:
        raise ValueError("A backlog is required for dependency analysis")
    context = [{
        "stable_id": item.stable_id, "item_type": item.__tablename__, "title": item.title,
        "description": item.description, "requirement_ids": json.loads(item.requirement_ids_json),
    } for item in items]
    shape = {"dependencies": [{
        "source_stable_id": "STORY-002", "target_stable_id": "STORY-001",
        "dependency_type": "requires | precedes | blocks | relates_to",
        "risk": "critical | high | medium | low", "explanation": "string", "confidence": 0.9,
    }]}
    prompt = "Analyze dependencies using this exact shape: " + json.dumps(shape) + "\n\nBACKLOG:\n" + json.dumps(context)
    known_ids = {item.stable_id for item in items}
    validation_error = ""
    for _ in range(2):
        raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
        try:
            batch = DependencyBatch.model_validate_json(raw)
        except ValidationError as error:
            validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + str(error)
            continue
        edges = [(item.source_stable_id, item.target_stable_id) for item in batch.dependencies]
        referenced_ids = {item_id for edge in edges for item_id in edge}
        if referenced_ids <= known_ids and not _has_cycle(edges):
            return DependencyGeneration(batch, hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        validation_error = "\nUse only supplied stable IDs and return an acyclic graph."
    raise ValueError("LLM dependency output failed validation after retry")


def _item_evidence(item) -> list[SourceReference]:
    provenance = json.loads(item.provenance_json)
    return [
        SourceReference.model_validate(reference)
        for reference in provenance.get("title", {}).get("source_references", [])
    ]


async def persist_dependencies(
    db: AsyncSession,
    project_id: str,
    session_id: str,
    batch: DependencyBatch,
) -> list[Dependency]:
    epics = (await db.execute(select(Epic).where(Epic.session_id == session_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id))).scalars().all()
    item_by_id = {item.stable_id: item for item in [*epics, *stories, *tasks]}
    records: list[Dependency] = []
    for draft in batch.dependencies:
        source = item_by_id[draft.source_stable_id]
        target = item_by_id[draft.target_stable_id]
        evidence = {
            (item.document_id, item.chunk_id): item
            for item in [*_item_evidence(source), *_item_evidence(target)]
        }
        values = {
            "dependency_type": draft.dependency_type,
            "risk": draft.risk,
            "explanation": draft.explanation,
        }
        provenance = {
            field_name: ProvenanceValue(
                value=value, origin="inferred", confidence=draft.confidence,
                source_references=list(evidence.values()), requires_review=True,
            ).model_dump(mode="json")
            for field_name, value in values.items()
        }
        record = Dependency(
            project_id=project_id, session_id=session_id,
            source_stable_id=draft.source_stable_id, target_stable_id=draft.target_stable_id,
            dependency_type=draft.dependency_type, risk=draft.risk,
            explanation=draft.explanation, confidence=draft.confidence,
            provenance_json=json.dumps(provenance),
        )
        db.add(record)
        records.append(record)
    await db.flush()
    return records


def dependency_to_dict(record: Dependency) -> dict[str, object]:
    return {
        "id": record.id, "source_stable_id": record.source_stable_id,
        "target_stable_id": record.target_stable_id, "dependency_type": record.dependency_type,
        "risk": record.risk, "explanation": record.explanation,
        "confidence": record.confidence, "provenance": json.loads(record.provenance_json),
    }