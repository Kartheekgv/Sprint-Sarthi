import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Task, UserStory
from app.providers.base import LLMProvider
from app.schemas.estimation import EstimationBatch
from app.schemas.provenance import ProvenanceValue, SourceReference


SYSTEM_PROMPT = """You are Sprint Sarthi's Estimation Agent. Return JSON only and never markdown.
Estimate every supplied story and task using relative complexity, uncertainty, integration effort, and testing effort. Story points must use 1, 2, 3, 5, 8, or 13. Task hours must be positive and no more than 200. Give a concise rationale. Do not alter scope, wording, priority, hierarchy, dependencies, assignments, or sprint placement. Estimates are recommendations requiring human review."""

STORIES_PER_BATCH = 10


@dataclass(frozen=True)
class EstimationGeneration:
    batch: EstimationBatch
    prompt_hash: str


async def generate_estimates(
    db: AsyncSession,
    session_id: str,
    provider: LLMProvider,
) -> EstimationGeneration:
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id).order_by(Task.stable_id))).scalars().all()
    if not stories or not tasks:
        raise ValueError("Stories and tasks are required for estimation")
    story_stable_by_id = {item.id: item.stable_id for item in stories}
    story_context = [{
            "stable_id": item.stable_id, "title": item.title, "description": item.description,
            "acceptance_criteria": json.loads(item.acceptance_criteria or "[]"), "priority": item.priority,
        } for item in stories]
    task_context = [{
            "stable_id": item.stable_id, "story_id": story_stable_by_id[item.story_id],
            "title": item.title, "description": item.description, "task_type": item.task_type,
            "priority": item.priority,
        } for item in tasks]
    shape = {
        "stories": [{"stable_id": "STORY-001", "story_points": 5, "rationale": "string", "confidence": 0.8}],
        "tasks": [{"stable_id": "TASK-001", "estimated_hours": 12, "rationale": "string", "confidence": 0.8}],
    }
    expected_story_ids = {item.stable_id for item in stories}
    expected_task_ids = {item.stable_id for item in tasks}
    merged_stories = {}
    merged_tasks = {}
    prompts = []
    for index in range(0, len(story_context), STORIES_PER_BATCH):
        batch_stories = story_context[index:index + STORIES_PER_BATCH]
        story_ids = {item["stable_id"] for item in batch_stories}
        context = {
            "stories": batch_stories,
            "tasks": [item for item in task_context if item["story_id"] in story_ids],
        }
        prompt = "Estimate the backlog using this exact shape: " + json.dumps(shape) + "\n\nBACKLOG:\n" + json.dumps(context)
        prompts.append(prompt)
        expected_local_tasks = {item["stable_id"] for item in context["tasks"]}
        validation_error = ""
        for _ in range(2):
            raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
            try:
                batch = EstimationBatch.model_validate_json(raw)
            except ValidationError as error:
                validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + str(error)
                continue
            batch_story_ids = [item.stable_id for item in batch.stories]
            batch_task_ids = [item.stable_id for item in batch.tasks]
            if (
                set(batch_story_ids) == story_ids and len(batch_story_ids) == len(story_ids)
                and set(batch_task_ids) == expected_local_tasks and len(batch_task_ids) == len(expected_local_tasks)
            ):
                merged_stories.update({item.stable_id: item for item in batch.stories})
                merged_tasks.update({item.stable_id: item for item in batch.tasks})
                break
            validation_error = "\nReturn every supplied story and task stable ID exactly once and do not invent IDs."
        else:
            raise ValueError(f"LLM estimation batch {index // STORIES_PER_BATCH + 1} failed validation after retry")
    if set(merged_stories) != expected_story_ids or set(merged_tasks) != expected_task_ids:
        raise ValueError("Merged estimation output does not cover the complete backlog")
    result = EstimationBatch(stories=list(merged_stories.values()), tasks=list(merged_tasks.values()))
    return EstimationGeneration(result, hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest())


def _set_estimate_provenance(record, value: int | float, rationale: str, confidence: float) -> None:
    provenance = json.loads(record.provenance_json)
    evidence = [
        SourceReference.model_validate(item)
        for item in provenance.get("title", {}).get("source_references", [])
    ]
    field_name = "story_points" if isinstance(record, UserStory) else "estimated_hours"
    for name, field_value in ((field_name, value), ("estimation_rationale", rationale)):
        provenance[name] = ProvenanceValue(
            value=field_value,
            origin="calculated",
            confidence=confidence,
            source_references=evidence,
            requires_review=True,
        ).model_dump(mode="json")
    record.provenance_json = json.dumps(provenance)


async def persist_estimates(
    db: AsyncSession,
    session_id: str,
    batch: EstimationBatch,
) -> tuple[list[UserStory], list[Task]]:
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id).order_by(Task.stable_id))).scalars().all()
    story_by_id = {item.stable_id: item for item in stories}
    task_by_id = {item.stable_id: item for item in tasks}
    for draft in batch.stories:
        record = story_by_id[draft.stable_id]
        record.story_points = draft.story_points
        record.estimation_rationale = draft.rationale
        _set_estimate_provenance(record, draft.story_points, draft.rationale, draft.confidence)
    for draft in batch.tasks:
        record = task_by_id[draft.stable_id]
        record.estimated_hours = draft.estimated_hours
        record.estimation_rationale = draft.rationale
        _set_estimate_provenance(record, draft.estimated_hours, draft.rationale, draft.confidence)
    await db.flush()
    return stories, tasks