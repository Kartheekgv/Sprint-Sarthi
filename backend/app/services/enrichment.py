import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Epic, Task, UserStory
from app.providers.base import LLMProvider
from app.services.prompting import compact_json
from app.schemas.enrichment import EnrichmentBatch
from app.schemas.provenance import ProvenanceValue, SourceReference


SYSTEM_PROMPT = """You are Sprint Sarthi's Enrichment Agent. Return JSON only and never markdown.
Enrich every supplied backlog item without changing its identity, hierarchy, title, description, or scope. Assign Critical, High, Medium, or Low priority based only on supplied evidence. Add concise, objectively testable acceptance criteria to epics and stories, preferably in Given/When/Then form. Improve epic business value. Do not estimate effort, identify dependencies, assign people, or place work into sprints."""

STORIES_PER_BATCH = 10


@dataclass(frozen=True)
class EnrichmentGeneration:
    batch: EnrichmentBatch
    prompt_hash: str


async def generate_enrichment(
    db: AsyncSession,
    session_id: str,
    provider: LLMProvider,
) -> EnrichmentGeneration:
    epics = (await db.execute(select(Epic).where(Epic.session_id == session_id).order_by(Epic.stable_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id).order_by(Task.stable_id))).scalars().all()
    if not epics or not stories or not tasks:
        raise ValueError("A complete backlog is required for enrichment")
    epic_stable_by_id = {item.id: item.stable_id for item in epics}
    story_stable_by_id = {item.id: item.stable_id for item in stories}
    epic_context = [{
            "stable_id": item.stable_id, "title": item.title, "description": item.description,
            "business_value": item.business_value, "requirement_ids": json.loads(item.requirement_ids_json),
        } for item in epics]
    story_context = [{
            "stable_id": item.stable_id, "epic_id": epic_stable_by_id[item.epic_id],
            "title": item.title, "user_story": item.user_story, "description": item.description,
            "requirement_ids": json.loads(item.requirement_ids_json),
        } for item in stories]
    task_context = [{
            "stable_id": item.stable_id, "story_id": story_stable_by_id[item.story_id],
            "title": item.title, "description": item.description, "task_type": item.task_type,
            "requirement_ids": json.loads(item.requirement_ids_json),
        } for item in tasks]
    shape = {
        "epics": [{"stable_id": "EPIC-001", "business_value": "string", "priority": "High", "acceptance_criteria": ["string"], "confidence": 0.9}],
        "stories": [{"stable_id": "STORY-001", "acceptance_criteria": ["string"], "priority": "High", "confidence": 0.9}],
        "tasks": [{"stable_id": "TASK-001", "priority": "High", "confidence": 0.9}],
    }
    expected = {
        "epics": {item.stable_id for item in epics},
        "stories": {item.stable_id for item in stories},
        "tasks": {item.stable_id for item in tasks},
    }
    merged = {"epics": {}, "stories": {}, "tasks": {}}
    prompts = []
    for index in range(0, len(story_context), STORIES_PER_BATCH):
        batch_stories = story_context[index:index + STORIES_PER_BATCH]
        story_ids = {item["stable_id"] for item in batch_stories}
        epic_ids = {item["epic_id"] for item in batch_stories}
        context = {
            "epics": [item for item in epic_context if item["stable_id"] in epic_ids],
            "stories": batch_stories,
            "tasks": [item for item in task_context if item["story_id"] in story_ids],
        }
        prompt = "Enrich the backlog using this exact shape: " + compact_json(shape) + "\n\nBACKLOG:\n" + compact_json(context)
        prompts.append(prompt)
        local_expected = {kind: {item["stable_id"] for item in values} for kind, values in context.items()}
        validation_error = ""
        for _ in range(2):
            raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
            try:
                batch = EnrichmentBatch.model_validate_json(raw)
            except ValidationError as error:
                validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + str(error)
                continue
            actual = {
                "epics": [item.stable_id for item in batch.epics],
                "stories": [item.stable_id for item in batch.stories],
                "tasks": [item.stable_id for item in batch.tasks],
            }
            if all(set(actual[kind]) == local_expected[kind] and len(actual[kind]) == len(local_expected[kind]) for kind in local_expected):
                for kind in merged:
                    merged[kind].update({item.stable_id: item for item in getattr(batch, kind)})
                break
            validation_error = "\nReturn every supplied stable ID exactly once and do not invent IDs."
        else:
            raise ValueError(f"LLM enrichment batch {index // STORIES_PER_BATCH + 1} failed validation after retry")
    if any(set(merged[kind]) != expected[kind] for kind in expected):
        raise ValueError("Merged enrichment output does not cover the complete backlog")
    result = EnrichmentBatch(**{kind: list(values.values()) for kind, values in merged.items()})
    return EnrichmentGeneration(result, hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest())


def _field_provenance(record, field_name: str, value: object, confidence: float) -> None:
    provenance = json.loads(record.provenance_json)
    source_values = provenance.get("title", {}).get("source_references", [])
    evidence = [SourceReference.model_validate(item) for item in source_values]
    provenance[field_name] = ProvenanceValue(
        value=value,
        origin="inferred",
        confidence=confidence,
        source_references=evidence,
        requires_review=True,
    ).model_dump(mode="json")
    record.provenance_json = json.dumps(provenance)


async def persist_enrichment(
    db: AsyncSession,
    session_id: str,
    batch: EnrichmentBatch,
) -> tuple[list[Epic], list[UserStory], list[Task]]:
    epics = (await db.execute(select(Epic).where(Epic.session_id == session_id).order_by(Epic.stable_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id).order_by(Task.stable_id))).scalars().all()
    epic_by_id = {item.stable_id: item for item in epics}
    story_by_id = {item.stable_id: item for item in stories}
    task_by_id = {item.stable_id: item for item in tasks}
    for draft in batch.epics:
        record = epic_by_id[draft.stable_id]
        record.business_value = draft.business_value
        record.priority = draft.priority
        record.acceptance_criteria = json.dumps(draft.acceptance_criteria)
        _field_provenance(record, "business_value", draft.business_value, draft.confidence)
        _field_provenance(record, "priority", draft.priority, draft.confidence)
        _field_provenance(record, "acceptance_criteria", draft.acceptance_criteria, draft.confidence)
    for draft in batch.stories:
        record = story_by_id[draft.stable_id]
        record.priority = draft.priority
        record.acceptance_criteria = json.dumps(draft.acceptance_criteria)
        _field_provenance(record, "priority", draft.priority, draft.confidence)
        _field_provenance(record, "acceptance_criteria", draft.acceptance_criteria, draft.confidence)
    for draft in batch.tasks:
        record = task_by_id[draft.stable_id]
        record.priority = draft.priority
        _field_provenance(record, "priority", draft.priority, draft.confidence)
    await db.flush()
    return epics, stories, tasks