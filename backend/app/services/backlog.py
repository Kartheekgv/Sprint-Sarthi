import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Decomposition, Epic, Feature, Task, UserStory
from app.providers.base import LLMProvider
from app.services.prompting import compact_json, json_repair_prompt
from app.schemas.backlog import BacklogBatch
from app.schemas.provenance import ProvenanceValue, SourceReference


SYSTEM_PROMPT = """You are Sprint Sarthi's Backlog Agent. Return JSON only and never markdown.
Transform the supplied decomposition records into a complete SAFe Epic -> Feature -> Story -> Task hierarchy. Use every decomposition ID at least once and only use supplied IDs. Anchor each Epic to an architecture layer or S-AD section. Keep each story independently valuable and each task concrete. Include evidence-supported functional, QA, enabler, infrastructure, security, compliance, and release work so the hierarchy reaches a shippable service. Every story and task needs an objective Definition of Done; every task also needs testable acceptance criteria. Do not add priority, estimates, dependencies, assignments, or sprint placement because later specialist agents own those fields. Temporary E/F/S/T keys only establish parent relationships; the server assigns stable IDs."""

DECOMPOSITIONS_PER_BATCH = 4


@dataclass(frozen=True)
class BacklogGeneration:
    batch: BacklogBatch
    prompt_hash: str


def _prune_orphan_hierarchy(raw: str) -> object:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return payload
    epics = payload.get("epics")
    features = payload.get("features")
    stories = payload.get("stories")
    tasks = payload.get("tasks")
    if not all(isinstance(collection, list) for collection in (epics, features, stories, tasks)):
        return payload

    used_story_keys = {
        item.get("parent_story_key") for item in tasks if isinstance(item, dict)
    }
    retained_stories = [
        item for item in stories
        if isinstance(item, dict) and item.get("story_key") in used_story_keys
    ]
    used_feature_keys = {item.get("parent_feature_key") for item in retained_stories}
    retained_features = [
        item for item in features
        if isinstance(item, dict) and item.get("feature_key") in used_feature_keys
    ]
    used_epic_keys = {item.get("parent_epic_key") for item in retained_features}
    retained_epics = [
        item for item in epics
        if isinstance(item, dict) and item.get("epic_key") in used_epic_keys
    ]
    return {
        **payload,
        "epics": retained_epics,
        "features": retained_features,
        "stories": retained_stories,
        "tasks": tasks,
    }


def _fallback_backlog_batch(batch_context: list[dict[str, object]]) -> BacklogBatch:
    capability = str(batch_context[0]["parent_capability"])
    epic_key = "E1"
    payload = {
        "epics": [{
            "epic_key": epic_key,
            "decomposition_ids": [item["decomposition_id"] for item in batch_context],
            "title": capability if len(capability) >= 5 else f"{capability} delivery capability",
            "description": f"Deliver the evidence-backed components grouped under {capability}.",
            "architecture_layer": capability,
            "business_value": "Delivers the source-backed architecture scope as reviewable increments.",
            "confidence": 0.7,
        }],
        "features": [],
        "stories": [],
        "tasks": [],
    }
    for index, item in enumerate(batch_context, 1):
        decomposition_id = str(item["decomposition_id"])
        title = str(item["title"])
        description = str(item["description"])
        payload["features"].append({
            "feature_key": f"F{index}", "parent_epic_key": epic_key,
            "decomposition_ids": [decomposition_id], "title": title,
            "description": description,
            "business_value": f"Delivers the capability supported by {decomposition_id}.",
            "confidence": 0.7,
        })
        payload["stories"].append({
            "story_key": f"S{index}", "parent_feature_key": f"F{index}",
            "decomposition_ids": [decomposition_id], "title": title,
            "user_story": f"As a stakeholder, I want {title} so that the documented capability is delivered.",
            "description": description,
            "definition_of_done": [f"The behavior described by {decomposition_id} is implemented, reviewed, and verified."],
            "confidence": 0.7,
        })
        payload["tasks"].append({
            "task_key": f"T{index}", "parent_story_key": f"S{index}",
            "decomposition_ids": [decomposition_id], "title": f"Implement {title}",
            "description": f"Implement and verify the source-backed scope described by {decomposition_id}.",
            "task_type": "implementation",
            "work_category": "enabler" if item["component_type"] == "technical_component" else "functional",
            "acceptance_criteria": [f"The documented behavior for {decomposition_id} is demonstrably implemented."],
            "definition_of_done": ["Implementation, review, automated verification, and traceability are complete."],
            "confidence": 0.7,
        })
    return BacklogBatch.model_validate(payload)


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
            "description": "string", "architecture_layer": "S-AD section or architecture layer",
            "business_value": "string", "confidence": 0.9,
        }],
        "features": [{
            "feature_key": "F1", "parent_epic_key": "E1", "decomposition_ids": ["DEC-001"],
            "title": "string", "description": "string", "business_value": "string", "confidence": 0.9,
        }],
        "stories": [{
            "story_key": "S1", "parent_feature_key": "F1", "decomposition_ids": ["DEC-001"],
            "title": "string", "user_story": "As a ..., I want ..., so that ...",
            "description": "string", "definition_of_done": ["objective completion check"], "confidence": 0.9,
        }],
        "tasks": [{
            "task_key": "T1", "parent_story_key": "S1", "decomposition_ids": ["DEC-001"],
            "title": "string", "description": "string",
            "task_type": "implementation | testing | documentation | analysis | configuration",
            "work_category": "functional | qa | enabler | infrastructure | security | compliance | release",
            "acceptance_criteria": ["testable statement"],
            "definition_of_done": ["objective completion check"],
            "confidence": 0.9,
        }],
    }
    context_batches = [context[index:index + DECOMPOSITIONS_PER_BATCH] for index in range(0, len(context), DECOMPOSITIONS_PER_BATCH)]
    merged_epics = []
    merged_features = []
    merged_stories = []
    merged_tasks = []
    prompts = []
    allocated_epics = 0
    allocated_features = 0
    allocated_stories = 0
    allocated_tasks = 0
    processed_decompositions = 0
    for batch_index, batch_context in enumerate(context_batches):
        processed_decompositions += len(batch_context)
        epic_quota = 30 * processed_decompositions // len(context) - allocated_epics
        feature_quota = 100 * processed_decompositions // len(context) - allocated_features
        story_quota = 100 * processed_decompositions // len(context) - allocated_stories
        task_quota = 300 * processed_decompositions // len(context) - allocated_tasks
        minimum_stories = len(batch_context)
        allocated_epics += epic_quota
        allocated_features += feature_quota
        allocated_stories += story_quota
        allocated_tasks += task_quota
        prompt = (
            "Generate an evidence-based backlog batch using this exact shape: " + compact_json(shape)
            + f"\nCreate no more than {epic_quota} epics, {feature_quota} features, and {task_quota} tasks. "
            + f"Create between {minimum_stories} and {story_quota} stories, with at least one independently valuable story for each supplied decomposition. "
            + "Create additional stories only for distinct work supported by the evidence; do not duplicate or pad scope. "
            + "Every story must have at least one task."
            + "\n\nDECOMPOSITIONS:\n" + compact_json(batch_context)
        )
        prompts.append(prompt)
        expected_ids = {item["decomposition_id"] for item in batch_context}
        attempt_prompt = prompt
        final_error = "unknown schema mismatch"
        generated = None
        for _ in range(4):
            raw = await provider.generate_text(attempt_prompt, SYSTEM_PROMPT)
            try:
                candidate = BacklogBatch.model_validate(_prune_orphan_hierarchy(raw))
            except (json.JSONDecodeError, ValidationError) as error:
                if isinstance(error, ValidationError):
                    issues = [
                        f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}"
                        for issue in error.errors(include_url=False, include_input=False)
                    ]
                else:
                    issues = ["Response is not valid JSON"]
                final_error = "; ".join(issues)
                attempt_prompt = json_repair_prompt(
                    raw, final_error, shape,
                    f"Use every supplied decomposition ID and stay within {epic_quota} epics, {feature_quota} features, {story_quota} stories, and {task_quota} tasks.",
                )
                continue
            referenced_ids = {
                item_id
                for collection in (candidate.epics, candidate.features, candidate.stories, candidate.tasks)
                for item in collection
                for item_id in item.decomposition_ids
            }
            if (
                referenced_ids == expected_ids
                and len(candidate.epics) <= epic_quota
                and len(candidate.features) <= feature_quota
                and len(candidate.stories) >= minimum_stories
                and len(candidate.stories) <= story_quota
                and len(candidate.tasks) <= task_quota
            ):
                generated = candidate
                break
            final_error = (
                "coverage or quota mismatch: use every supplied decomposition ID and no others; "
                f"at most {epic_quota} epics, at most {feature_quota} features, between {minimum_stories} and {story_quota} stories, "
                f"and at most {task_quota} tasks."
            )
            attempt_prompt = json_repair_prompt(raw, final_error, shape, final_error)
        if generated is None:
            generated = _fallback_backlog_batch(batch_context)

        epic_key_map = {
            item.epic_key: f"E{len(merged_epics) + offset}"
            for offset, item in enumerate(generated.epics, start=1)
        }
        feature_key_map = {
            item.feature_key: f"F{len(merged_features) + offset}"
            for offset, item in enumerate(generated.features, start=1)
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
        merged_features.extend(item.model_copy(update={
            "feature_key": feature_key_map[item.feature_key],
            "parent_epic_key": epic_key_map[item.parent_epic_key],
        }) for item in generated.features)
        merged_stories.extend(item.model_copy(update={
            "story_key": story_key_map[item.story_key],
            "parent_feature_key": feature_key_map[item.parent_feature_key],
        }) for item in generated.stories)
        merged_tasks.extend(item.model_copy(update={
            "task_key": task_key_map[item.task_key],
            "parent_story_key": story_key_map[item.parent_story_key],
        }) for item in generated.tasks)

    merged = BacklogBatch(epics=merged_epics, features=merged_features, stories=merged_stories, tasks=merged_tasks)
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
) -> tuple[list[Epic], list[Feature], list[UserStory], list[Task]]:
    decompositions = (await db.execute(
        select(Decomposition).where(Decomposition.session_id == session_id)
    )).scalars().all()
    decomposition_by_id = {item.stable_id: item for item in decompositions}
    supplied_ids = {
        item_id
        for collection in (batch.epics, batch.features, batch.stories, batch.tasks)
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
            "title": draft.title, "description": draft.description, "architecture_layer": draft.architecture_layer,
            "business_value": draft.business_value, "priority": "Unknown",
            "acceptance_criteria": [],
        }
        record = Epic(
            project_id=project_id, session_id=session_id, stable_id=f"EPIC-{offset:03d}",
            decomposition_ids_json=json.dumps(draft.decomposition_ids),
            requirement_ids_json=json.dumps(requirement_ids), title=draft.title,
            description=draft.description, architecture_layer=draft.architecture_layer, business_value=draft.business_value,
            priority="Unknown", acceptance_criteria="[]",
            source_references_json=json.dumps(source_references),
            provenance_json=_provenance(values, draft.confidence, evidence),
        )
        db.add(record)
        epics.append(record)
        epic_by_key[draft.epic_key] = record
    await db.flush()

    feature_count = await db.scalar(select(func.count(Feature.id))) or 0
    features: list[Feature] = []
    feature_by_key: dict[str, Feature] = {}
    for offset, draft in enumerate(batch.features, start=feature_count + 1):
        requirement_ids, source_references, evidence = _lineage(decomposition_by_id, draft.decomposition_ids)
        values = {"title": draft.title, "description": draft.description, "business_value": draft.business_value}
        record = Feature(
            project_id=project_id, session_id=session_id, epic_id=epic_by_key[draft.parent_epic_key].id,
            stable_id=f"FEATURE-{offset:03d}", decomposition_ids_json=json.dumps(draft.decomposition_ids),
            requirement_ids_json=json.dumps(requirement_ids), title=draft.title,
            description=draft.description, business_value=draft.business_value,
            source_references_json=json.dumps(source_references),
            provenance_json=_provenance(values, draft.confidence, evidence),
        )
        db.add(record)
        features.append(record)
        feature_by_key[draft.feature_key] = record
    await db.flush()

    story_count = await db.scalar(select(func.count(UserStory.id))) or 0
    stories: list[UserStory] = []
    story_by_key: dict[str, UserStory] = {}
    for offset, draft in enumerate(batch.stories, start=story_count + 1):
        requirement_ids, source_references, evidence = _lineage(decomposition_by_id, draft.decomposition_ids)
        values = {
            "title": draft.title, "user_story": draft.user_story, "description": draft.description,
            "acceptance_criteria": [], "definition_of_done": draft.definition_of_done,
            "priority": "Unknown", "story_points": None,
        }
        feature = feature_by_key[draft.parent_feature_key]
        record = UserStory(
            project_id=project_id, session_id=session_id, epic_id=feature.epic_id, feature_id=feature.id,
            stable_id=f"STORY-{offset:03d}", decomposition_ids_json=json.dumps(draft.decomposition_ids),
            requirement_ids_json=json.dumps(requirement_ids), title=draft.title,
            user_story=draft.user_story, description=draft.description,
            acceptance_criteria="[]", definition_of_done_json=json.dumps(draft.definition_of_done),
            priority="Unknown", story_points=None,
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
            "task_type": draft.task_type, "work_category": draft.work_category,
            "acceptance_criteria": draft.acceptance_criteria, "definition_of_done": draft.definition_of_done,
            "priority": "Unknown", "estimated_hours": None,
        }
        record = Task(
            project_id=project_id, session_id=session_id, story_id=story_by_key[draft.parent_story_key].id,
            stable_id=f"TASK-{offset:03d}", decomposition_ids_json=json.dumps(draft.decomposition_ids),
            requirement_ids_json=json.dumps(requirement_ids), title=draft.title,
            description=draft.description, task_type=draft.task_type, work_category=draft.work_category,
            acceptance_criteria_json=json.dumps(draft.acceptance_criteria),
            definition_of_done_json=json.dumps(draft.definition_of_done), priority="Unknown",
            estimated_hours=None, source_references_json=json.dumps(source_references),
            provenance_json=_provenance(values, draft.confidence, evidence),
        )
        db.add(record)
        tasks.append(record)
    await db.flush()
    return epics, features, stories, tasks


def backlog_to_dicts(
    epics: list[Epic], features: list[Feature], stories: list[UserStory], tasks: list[Task]
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    epic_stable_by_id = {item.id: item.stable_id for item in epics}
    story_stable_by_id = {item.id: item.stable_id for item in stories}
    feature_stable_by_id = {item.id: item.stable_id for item in features}
    epic_rows = [{
        "id": item.id, "stable_id": item.stable_id,
        "decomposition_ids": json.loads(item.decomposition_ids_json),
        "requirement_ids": json.loads(item.requirement_ids_json), "title": item.title,
        "description": item.description, "architecture_layer": item.architecture_layer,
        "business_value": item.business_value,
        "priority": item.priority, "source_references": json.loads(item.source_references_json),
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in epics]
    feature_rows = [{
        "id": item.id, "stable_id": item.stable_id, "epic_stable_id": epic_stable_by_id[item.epic_id],
        "decomposition_ids": json.loads(item.decomposition_ids_json),
        "requirement_ids": json.loads(item.requirement_ids_json), "title": item.title,
        "description": item.description, "business_value": item.business_value,
        "source_references": json.loads(item.source_references_json),
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in features]
    story_rows = [{
        "id": item.id, "stable_id": item.stable_id, "epic_stable_id": epic_stable_by_id[item.epic_id],
        "feature_stable_id": feature_stable_by_id.get(item.feature_id, "FEATURE-LEGACY"),
        "decomposition_ids": json.loads(item.decomposition_ids_json),
        "requirement_ids": json.loads(item.requirement_ids_json), "title": item.title,
        "user_story": item.user_story, "description": item.description,
        "acceptance_criteria": json.loads(item.acceptance_criteria or "[]"), "priority": item.priority,
        "definition_of_done": json.loads(item.definition_of_done_json or "[]"),
        "story_points": item.story_points, "estimation_rationale": item.estimation_rationale,
        "source_references": json.loads(item.source_references_json),
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in stories]
    task_rows = [{
        "id": item.id, "stable_id": item.stable_id, "story_stable_id": story_stable_by_id[item.story_id],
        "decomposition_ids": json.loads(item.decomposition_ids_json),
        "requirement_ids": json.loads(item.requirement_ids_json), "title": item.title,
        "description": item.description, "task_type": item.task_type, "work_category": item.work_category,
        "acceptance_criteria": json.loads(item.acceptance_criteria_json or "[]"),
        "definition_of_done": json.loads(item.definition_of_done_json or "[]"), "priority": item.priority,
        "estimated_hours": item.estimated_hours, "estimation_rationale": item.estimation_rationale,
        "source_references": json.loads(item.source_references_json),
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in tasks]
    return epic_rows, feature_rows, story_rows, task_rows