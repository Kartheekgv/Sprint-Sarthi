import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.entities import Decomposition, Requirement
from app.providers.base import LLMProvider
from app.services.prompting import compact_json
from app.schemas.decomposition import DecompositionBatch
from app.schemas.provenance import ProvenanceValue, SourceReference


SYSTEM_PROMPT = """You are Sprint Sarthi's Decomposition Agent. Return JSON only and never markdown.
Break requirements into independent, understandable, deliverable components. Split compound requirements and follow INVEST for story-sized work. Preserve supplied requirement IDs. Do not invent scope. Use technical_component only when technical decomposition is explicit in the requirement; otherwise prefer business capabilities, features, or workflows. Every requirement must appear in at least one decomposition."""


@dataclass(frozen=True)
class DecompositionGeneration:
    batch: DecompositionBatch
    prompt_hash: str


async def generate_decompositions(
    db: AsyncSession,
    session_id: str,
    provider: LLMProvider,
) -> DecompositionGeneration:
    requirements = (await db.execute(
        select(Requirement).where(Requirement.session_id == session_id).order_by(Requirement.stable_id)
    )).scalars().all()
    if not requirements:
        raise ValueError("No requirements are available for decomposition")
    requirement_ids = {requirement.stable_id for requirement in requirements}
    requirement_context = [{
        "requirement_id": requirement.stable_id,
        "title": requirement.title,
        "description": requirement.description,
        "category": requirement.category,
        "actors": json.loads(requirement.actors_json),
        "systems": json.loads(requirement.systems_json),
        "business_rules": json.loads(requirement.business_rules_json),
        "constraints": json.loads(requirement.constraints_json),
        "assumptions": json.loads(requirement.assumptions_json),
        "source_references": json.loads(requirement.source_references_json),
    } for requirement in requirements]
    shape = {"decompositions": [{
        "requirement_ids": ["REQ-001"],
        "parent_capability": "string",
        "component_type": "business_capability | feature | workflow | technical_component",
        "title": "string",
        "description": "string",
        "suggested_backlog_level": "epic | story | task",
        "rationale": "string",
        "confidence": 0.9,
    }]}
    prompt = "Generate decomposition records using this exact shape: " + compact_json(shape) + "\n\nREQUIREMENTS:\n" + compact_json(requirement_context)
    validation_error = ""
    for _ in range(2):
        raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
        try:
            batch = DecompositionBatch.model_validate_json(raw)
        except ValidationError as error:
            validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + str(error)
            continue
        referenced_ids = {item_id for item in batch.decompositions for item_id in item.requirement_ids}
        if referenced_ids == requirement_ids:
            return DecompositionGeneration(batch, hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        validation_error = "\nUse only supplied requirement IDs and include every supplied requirement at least once."
    raise ValueError("LLM decomposition output failed validation after retry")


def _source_evidence(requirements: list[Requirement]) -> list[SourceReference]:
    evidence: dict[tuple[str, str], SourceReference] = {}
    for requirement in requirements:
        provenance = json.loads(requirement.provenance_json)
        for reference in provenance.get("title", {}).get("source_references", []):
            source = SourceReference.model_validate(reference)
            evidence[(source.document_id, source.chunk_id)] = source
    return list(evidence.values())


async def persist_decompositions(
    db: AsyncSession,
    project_id: str,
    session_id: str,
    batch: DecompositionBatch,
) -> list[Decomposition]:
    requirements = (await db.execute(
        select(Requirement).where(Requirement.session_id == session_id)
    )).scalars().all()
    requirement_by_id = {requirement.stable_id: requirement for requirement in requirements}
    existing_count = await db.scalar(select(func.count(Decomposition.id)).where(Decomposition.project_id == project_id))
    records: list[Decomposition] = []
    for offset, draft in enumerate(batch.decompositions, start=(existing_count or 0) + 1):
        linked = [requirement_by_id[item_id] for item_id in draft.requirement_ids]
        source_references = sorted({
            reference for requirement in linked for reference in json.loads(requirement.source_references_json)
        })
        evidence = _source_evidence(linked)
        provenance = {
            field_name: ProvenanceValue(
                value=value,
                origin="inferred",
                confidence=draft.confidence,
                source_references=evidence,
                requires_review=True,
            ).model_dump(mode="json")
            for field_name, value in {
                "parent_capability": draft.parent_capability,
                "component_type": draft.component_type,
                "title": draft.title,
                "description": draft.description,
                "suggested_backlog_level": draft.suggested_backlog_level,
                "rationale": draft.rationale,
            }.items()
        }
        record = Decomposition(
            project_id=project_id,
            session_id=session_id,
            stable_id=f"DEC-{offset:03d}",
            requirement_ids_json=json.dumps(draft.requirement_ids),
            parent_capability=draft.parent_capability,
            component_type=draft.component_type,
            title=draft.title,
            description=draft.description,
            suggested_backlog_level=draft.suggested_backlog_level,
            rationale=draft.rationale,
            source_references_json=json.dumps(source_references),
            confidence=draft.confidence,
            provenance_json=json.dumps(provenance),
        )
        db.add(record)
        records.append(record)
    await db.flush()
    return records


def decomposition_to_dict(record: Decomposition) -> dict[str, object]:
    return {
        "id": record.id,
        "stable_id": record.stable_id,
        "requirement_ids": json.loads(record.requirement_ids_json),
        "parent_capability": record.parent_capability,
        "component_type": record.component_type,
        "title": record.title,
        "description": record.description,
        "suggested_backlog_level": record.suggested_backlog_level,
        "rationale": record.rationale,
        "source_references": json.loads(record.source_references_json),
        "confidence": record.confidence,
        "provenance": json.loads(record.provenance_json),
        "status": record.status,
    }