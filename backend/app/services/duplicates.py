import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import DuplicateCandidate, Epic, Task, UserStory
from app.providers.base import LLMProvider
from app.services.prompting import compact_json
from app.schemas.duplicates import DuplicateBatch
from app.schemas.provenance import ProvenanceValue


SYSTEM_PROMPT = """You are Sprint Sarthi's Duplicate Agent. Return JSON only and never markdown.
Identify semantically overlapping backlog items using only supplied IDs and content. Compare items at the same hierarchy level. Return each pair once in ascending stable-ID order. Return an empty list when no defensible candidate exists. Recommendations are review-only; never merge, delete, or edit backlog items."""


@dataclass(frozen=True)
class DuplicateGeneration:
    batch: DuplicateBatch
    prompt_hash: str


def _filter_duplicate_candidates(
    batch: DuplicateBatch,
    known_ids: set[str],
    type_by_id: dict[str, str],
) -> tuple[DuplicateBatch, list[str]]:
    unknown_ids = sorted({
        stable_id
        for item in batch.candidates
        for stable_id in (item.source_stable_id, item.target_stable_id)
        if stable_id not in known_ids
    })
    candidates_by_pair = {}
    for candidate in batch.candidates:
        if candidate.source_stable_id not in type_by_id or candidate.target_stable_id not in type_by_id:
            continue
        if type_by_id[candidate.source_stable_id] != type_by_id[candidate.target_stable_id]:
            continue
        pair = (candidate.source_stable_id, candidate.target_stable_id)
        current = candidates_by_pair.get(pair)
        if current is None or candidate.confidence > current.confidence:
            candidates_by_pair[pair] = candidate
    return DuplicateBatch(candidates=list(candidates_by_pair.values())), unknown_ids


async def generate_duplicates(db: AsyncSession, session_id: str, provider: LLMProvider) -> DuplicateGeneration:
    epics = (await db.execute(select(Epic).where(Epic.session_id == session_id).order_by(Epic.stable_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id).order_by(Task.stable_id))).scalars().all()
    items = [*epics, *stories, *tasks]
    context = [{"stable_id": item.stable_id, "title": item.title, "description": item.description} for item in items]
    shape = {"candidates": [{
        "source_stable_id": "STORY-001", "target_stable_id": "STORY-002",
        "similarity": 0.9, "rationale": "string",
        "recommendation": "merge | keep_both | clarify", "confidence": 0.85,
    }]}
    prompt = "Find duplicate candidates using this exact shape: " + compact_json(shape) + "\n\nBACKLOG:\n" + compact_json(context)
    known_ids = {item.stable_id for item in items}
    type_by_id = {item.stable_id: item.stable_id.split("-")[0] for item in items}
    validation_error = ""
    final_error = "unknown duplicate mismatch"
    for _ in range(3):
        raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
        try:
            batch = DuplicateBatch.model_validate_json(raw)
        except ValidationError as error:
            issues = [
                f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}"
                for issue in error.errors(include_url=False, include_input=False)
            ]
            final_error = "; ".join(issues)
            validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + final_error
            continue
        normalized, unknown_ids = _filter_duplicate_candidates(batch, known_ids, type_by_id)
        if not unknown_ids:
            return DuplicateGeneration(normalized, hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        final_error = "unknown item IDs: " + ", ".join(unknown_ids)
        validation_error = "\nUse only supplied IDs. Correct: " + final_error
    raise ValueError(f"LLM duplicate output failed validation after 3 attempts: {final_error}")


async def persist_duplicates(db: AsyncSession, project_id: str, session_id: str, batch: DuplicateBatch) -> list[DuplicateCandidate]:
    records = []
    for draft in batch.candidates:
        provenance = {
            field: ProvenanceValue(value=value, origin="inferred", confidence=draft.confidence, source_references=[], requires_review=True).model_dump(mode="json")
            for field, value in {"similarity": draft.similarity, "rationale": draft.rationale, "recommendation": draft.recommendation}.items()
        }
        record = DuplicateCandidate(
            project_id=project_id, session_id=session_id,
            source_stable_id=draft.source_stable_id, target_stable_id=draft.target_stable_id,
            similarity=draft.similarity, rationale=draft.rationale,
            recommendation=draft.recommendation, confidence=draft.confidence,
            provenance_json=json.dumps(provenance), status="candidate",
        )
        db.add(record)
        records.append(record)
    await db.flush()
    return records


def duplicate_to_dict(record: DuplicateCandidate) -> dict[str, object]:
    return {
        "id": record.id, "source_stable_id": record.source_stable_id,
        "target_stable_id": record.target_stable_id, "similarity": record.similarity,
        "rationale": record.rationale, "recommendation": record.recommendation,
        "confidence": record.confidence, "provenance": json.loads(record.provenance_json),
        "status": record.status,
    }