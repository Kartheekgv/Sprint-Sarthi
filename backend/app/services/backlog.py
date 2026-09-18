import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Decomposition, Epic, Task, UserStory
from app.providers.base import LLMProvider
from app.services.prompting import compact_json
from app.schemas.backlog import BacklogBatch
from app.schemas.provenance import ProvenanceValue, SourceReference


SYSTEM_PROMPT = """You are Sprint Sarthi's Backlog Agent. Return JSON only and never markdown.
Transform the supplied decomposition records into a complete Epic -> Story -> Task hierarchy. Use every decomposition ID at least once and only use supplied IDs. Keep each story independently valuable and each task concrete. Do not add acceptance criteria, priority, estimates, dependencies, assignments, or sprint placement because later specialist agents own those fields. Temporary E/S/T keys only establish parent relationships; the server assigns stable IDs."""

DECOMPOSITIONS_PER_BATCH = 8


@dataclass(frozen=True)
class BacklogGeneration:
    batch: BacklogBatch
    prompt_hash: str


async def generate_backlog(
    db: AsyncSession,
    session_id: str,
    provider: LLMProvider,
) -> BacklogGeneration:
    decompositions = (await db.execute(
        select(Decomposition)
        .where(Decomposition.session_id == session_id)
        .order_by(Decomposition.stable_id)
    )).scalars().all()
    if not decompositions:
        raise ValueError("No decompositions are available for backlog generation")
    context = [{
        "decomposition_id": item.stable_id,
        "requirement_ids": json.loads(item.requirement_ids_json),
        "parent_capability": item.parent_capability,
        "component_type": item.component_type,
        "title": item.title,
        "description": item.description,
        "suggested_backlog_level": item.suggested_backlog_level,
        "rationale": item.rationale,
    } for item in decompositions]
    shape = {
        "epics": [{
            "epic_key": "E1", "decomposition_ids": ["DEC-001"], "title": "string",
            "description": "string", "business_value": "string", "confidence": 0.9,
        }],
        "stories": [{
            "story_key": "S1", "parent_epic_key": "E1", "decomposition_ids": ["DEC-001"],
            "title": "string", "user_story": "As a ..., I want ..., so that ...",
            "description": "string", "confidence": 0.9,
        }],
        "tasks": [{
            "task_key": "T1", "parent_story_key": "S1", "decomposition_ids": ["DEC-001"],
            "title": "string", "description": "string",
            "task_type": "implementation | testing | documentation | analysis | configuration",
            "confidence": 0.9,
        }],
    }
    context_batches = [context[index:index + DECOMPOSITIONS_PER_BATCH] for index in range(0, len(context), DECOMPOSITIONS_PER_BATCH)]
    merged_epics = []
    merged_stories = []
    merged_tasks = []
    prompts = []
    allocated_epics = 0
    allocated_stories = 0
    allocated_tasks = 0
    processed_decompositions = 0
    for batch_index, batch_context in enumerate(context_batches):
        processed_decompositions += len(batch_context)
        epic_quota = 30 * processed_decompositions // len(context) - allocated_epics
        story_quota = 100 * processed_decompositions // len(context) - allocated_stories
        task_quota = 300 * processed_decompositions // len(context) - allocated_tasks
        allocated_epics += epic_quota
        allocated_stories += story_quota
        allocated_tasks += task_quota
        prompt = (
            "Generate an evidence-based backlog batch using this exact shape: " + compact_json(shape)
            + f"\nCreate no more than {epic_quota} epics, {story_quota} stories, and {task_quota} tasks. "
            + "Create only distinct work supported by this batch; do not pad to the limits. "
            + "Every story must have at least one task."
            + "\n\nDECOMPOSITIONS:\n" + compact_json(batch_context)
        )
        prompts.append(prompt)
        expected_ids = {item["decomposition_id"] for item in batch_context}
        validation_error = ""
        generated = None
        for _ in range(3):
            raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
            try:
                candidate = BacklogBatch.model_validate_json(raw)
            except ValidationError as error:
                validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + str(error)
                continue
            referenced_ids = {
                item_id
                for collection in (candidate.epics, candidate.stories, candidate.tasks)
                for item in collection
                for item_id in item.decomposition_ids
            }
            if (
                referenced_ids == expected_ids
                and len(candidate.epics) <= epic_quota
                and len(candidate.stories) <= story_quota
                and len(candidate.tasks) <= task_quota
            ):
                generated = candidate
                break
            validation_error = (
                "\nUse every supplied decomposition ID and no others. Stay within the exact batch limits: "
                f"{epic_quota} epics, {story_quota} stories, {task_quota} tasks."
            )
        if generated is None:
            raise ValueError(f"LLM backlog batch {batch_index + 1} failed validation after 3 attempts")

        epic_key_map = {
            item.epic_key: f"E{len(merged_epics) + offset}"
            for offset, item in enumerate(generated.epics, start=1)
        }
        story_key_map = {
            item.story_key: f"S{len(merged_stories) + offset}"
            for offset, item in enumerate(generated.stories, start=1)
        }
        task_key_map = {
            item.task_key: f"T{len(merged_tasks) + offset}"
            for offset, item in enumerate(generated.tasks, start=1)
        }
        merged_epics.extend(item.model_copy(update={"epic_key": epic_key_map[item.epic_key]}) for item in generated.epics)
        merged_stories.extend(item.model_copy(update={
            "story_key": story_key_map[item.story_key],
            "parent_epic_key": epic_key_map[item.parent_epic_key],
        }) for item in generated.stories)
        merged_tasks.extend(item.model_copy(update={
            "task_key": task_key_map[item.task_key],
            "parent_story_key": story_key_map[item.parent_story_key],
        }) for item in generated.tasks)

    merged = BacklogBatch(epics=merged_epics, stories=merged_stories, tasks=merged_tasks)
    return BacklogGeneration(merged, hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest())


def _lineage(
    decomposition_by_id: dict[str, Decomposition],
    decomposition_ids: list[str],
) -> tuple[list[str], list[str], list[SourceReference]]:
    linked = [decomposition_by_id[item_id] for item_id in decomposition_ids]
    requirement_ids = sorted({
        requirement_id for item in linked for requirement_id in json.loads(item.requirement_ids_json)
    })
    source_references = sorted({
        reference for item in linked for reference in json.loads(item.source_references_json)
    })
    evidence: dict[tuple[str, str], SourceReference] = {}
    for item in linked:
        provenance = json.loads(item.provenance_json)
        for reference in provenance.get("title", {}).get("source_references", []):
            source = SourceReference.model_validate(reference)
            evidence[(source.document_id, source.chunk_id)] = source
    return requirement_ids, source_references, list(evidence.values())


def _provenance(values: dict[str, object], confidence: float, evidence: list[SourceReference]) -> str:
    return json.dumps({
        field_name: ProvenanceValue(
            value=value,
            origin="inferred",
            confidence=confidence,
            source_references=evidence,
            requires_review=True,
        ).model_dump(mode="json")
        for field_name, value in values.items()
    })


async def persist_backlog(
    db: AsyncSession,
    project_id: str,
    session_id: str,
    batch: BacklogBatch,
) -> tuple[list[Epic], list[UserStory], list[Task]]:
    decompositions = (await db.execute(
        select(Decomposition).where(Decomposition.session_id == session_id)
    )).scalars().all()
    decomposition_by_id = {item.stable_id: item for item in decompositions}
    supplied_ids = {
        item_id
        for collection in (batch.epics, batch.stories, batch.tasks)
        for item in collection
        for item_id in item.decomposition_ids
    }
    if supplied_ids != set(decomposition_by_id):
        raise ValueError("Backlog contains invalid or missing decomposition IDs")

    epic_count = await db.scalar(select(func.count(Epic.id))) or 0
    epics: list[Epic] = []
    epic_by_key: dict[str, Epic] = {}
    for offset, draft in enumerate(batch.epics, start=epic_count + 1):
        requirement_ids, source_references, evidence = _lineage(decomposition_by_id, draft.decomposition_ids)
        values = {
            "title": draft.title, "description": draft.description,
            "business_value": draft.business_value, "priority": "Unknown",
            "acceptance_criteria": [],
        }
        record = Epic(
            project_id=project_id, session_id=session_id, stable_id=f"EPIC-{offset:03d}",
            decomposition_ids_json=json.dumps(draft.decomposition_ids),
            requirement_ids_json=json.dumps(requirement_ids), title=draft.title,
            description=draft.description, business_value=draft.business_value,
            priority="Unknown", acceptance_criteria="[]",
            source_references_json=json.dumps(source_references),
            provenance_json=_provenance(values, draft.confidence, evidence),
        )
        db.add(record)
        epics.append(record)
        epic_by_key[draft.epic_key] = record
    await db.flush()

    story_count = await db.scalar(select(func.count(UserStory.id))) or 0
    stories: list[UserStory] = []
    story_by_key: dict[str, UserStory] = {}
    for offset, draft in enumerate(batch.stories, start=story_count + 1):
        requirement_ids, source_references, evidence = _lineage(decomposition_by_id, draft.decomposition_ids)
        values = {
            "title": draft.title, "user_story": draft.user_story, "description": draft.description,
            "acceptance_criteria": [], "priority": "Unknown", "story_points": None,
        }
        record = UserStory(
            project_id=project_id, session_id=session_id, epic_id=epic_by_key[draft.parent_epic_key].id,
            stable_id=f"STORY-{offset:03d}", decomposition_ids_json=json.dumps(draft.decomposition_ids),
            requirement_ids_json=json.dumps(requirement_ids), title=draft.title,
            user_story=draft.user_story, description=draft.description,
            acceptance_criteria="[]", priority="Unknown", story_points=None,
            source_references_json=json.dumps(source_references),
            provenance_json=_provenance(values, draft.confidence, evidence),
        )
        db.add(record)
        stories.append(record)
        story_by_key[draft.story_key] = record
    await db.flush()

    task_count = await db.scalar(select(func.count(Task.id))) or 0
    tasks: list[Task] = []
    for offset, draft in enumerate(batch.tasks, start=task_count + 1):
        requirement_ids, source_references, evidence = _lineage(decomposition_by_id, draft.decomposition_ids)
        values = {
            "title": draft.title, "description": draft.description,
            "task_type": draft.task_type, "priority": "Unknown", "estimated_hours": None,
        }
        record = Task(
            project_id=project_id, session_id=session_id, story_id=story_by_key[draft.parent_story_key].id,
            stable_id=f"TASK-{offset:03d}", decomposition_ids_json=json.dumps(draft.decomposition_ids),
            requirement_ids_json=json.dumps(requirement_ids), title=draft.title,
            description=draft.description, task_type=draft.task_type, priority="Unknown",
            estimated_hours=None, source_references_json=json.dumps(source_references),
            provenance_json=_provenance(values, draft.confidence, evidence),
        )
        db.add(record)
        tasks.append(record)
    await db.flush()
    return epics, stories, tasks


def backlog_to_dicts(
    epics: list[Epic], stories: list[UserStory], tasks: list[Task]
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    epic_stable_by_id = {item.id: item.stable_id for item in epics}
    story_stable_by_id = {item.id: item.stable_id for item in stories}
    epic_rows = [{
        "id": item.id, "stable_id": item.stable_id,
        "decomposition_ids": json.loads(item.decomposition_ids_json),
        "requirement_ids": json.loads(item.requirement_ids_json), "title": item.title,
        "description": item.description, "business_value": item.business_value,
        "priority": item.priority, "source_references": json.loads(item.source_references_json),
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in epics]
    story_rows = [{
        "id": item.id, "stable_id": item.stable_id, "epic_stable_id": epic_stable_by_id[item.epic_id],
        "decomposition_ids": json.loads(item.decomposition_ids_json),
        "requirement_ids": json.loads(item.requirement_ids_json), "title": item.title,
        "user_story": item.user_story, "description": item.description,
        "acceptance_criteria": json.loads(item.acceptance_criteria or "[]"), "priority": item.priority,
        "story_points": item.story_points, "estimation_rationale": item.estimation_rationale,
        "source_references": json.loads(item.source_references_json),
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in stories]
    task_rows = [{
        "id": item.id, "stable_id": item.stable_id, "story_stable_id": story_stable_by_id[item.story_id],
        "decomposition_ids": json.loads(item.decomposition_ids_json),
        "requirement_ids": json.loads(item.requirement_ids_json), "title": item.title,
        "description": item.description, "task_type": item.task_type, "priority": item.priority,
        "estimated_hours": item.estimated_hours, "estimation_rationale": item.estimation_rationale,
        "source_references": json.loads(item.source_references_json),
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in tasks]
    return epic_rows, story_rows, task_rows