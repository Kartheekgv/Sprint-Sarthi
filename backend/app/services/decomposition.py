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
Break requirements into independent, understandable, deliverable components. Split compound requirements and follow INVEST for story-sized work. Produce multiple components when a requirement contains distinct user outcomes, workflows, rules, integrations, or quality concerns. Preserve supplied requirement IDs. Do not invent scope. Use technical_component only when technical decomposition is explicit in the requirement; otherwise prefer business capabilities, features, or workflows. Every requirement must appear in at least one decomposition."""

REQUIREMENTS_PER_BATCH = 10
MAX_DECOMPOSITIONS = 100


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
    context_batches = [
        requirement_context[index:index + REQUIREMENTS_PER_BATCH]
        for index in range(0, len(requirement_context), REQUIREMENTS_PER_BATCH)
    ]
    merged_decompositions = []
    prompts: list[str] = []
    allocated = 0
    processed = 0
    for batch_index, batch_context in enumerate(context_batches):
        processed += len(batch_context)
        quota = MAX_DECOMPOSITIONS * processed // len(requirement_context) - allocated
        allocated += quota
        prompt = (
            "Generate decomposition records using this exact shape: " + compact_json(shape)
            + f"\nReturn between {len(batch_context)} and {quota} decomposition records. "
            + "Every supplied requirement needs at least one record; split compound requirements when evidence supports distinct deliverable outcomes."
            + "\n\nREQUIREMENTS:\n" + compact_json(batch_context)
        )
        prompts.append(prompt)
        expected_ids = {item["requirement_id"] for item in batch_context}
        validation_error = ""
        for _ in range(3):
            raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
            try:
                batch = DecompositionBatch.model_validate_json(raw)
            except ValidationError as error:
                validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + str(error)
                continue
            referenced_ids = {item_id for item in batch.decompositions for item_id in item.requirement_ids}
            if referenced_ids == expected_ids and len(batch.decompositions) <= quota:
                merged_decompositions.extend(batch.decompositions)
                break
            validation_error = (
                "\nUse only supplied requirement IDs, include every supplied requirement at least once, "
                f"and return no more than {quota} records."
            )
        else:
            raise ValueError(f"LLM decomposition batch {batch_index + 1} failed validation after 3 attempts")

    merged = DecompositionBatch(decompositions=merged_decompositions)
    return DecompositionGeneration(merged, hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest())


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