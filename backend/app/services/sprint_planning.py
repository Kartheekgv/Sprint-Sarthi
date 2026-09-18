import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    AssignmentRecommendation, Dependency, Sprint, SprintPlanDecision, TeamMember, UserStory,
)
from app.providers.base import LLMProvider
from app.services.prompting import compact_json
from app.schemas.provenance import ProvenanceValue
from app.schemas.sprint_planning import SprintPlanningBatch


SYSTEM_PROMPT = """You are Sprint Sarthi's Sprint Agent. Return JSON only and never markdown.
Create a capacity-aware recommendation for every supplied story. Use only supplied sprint and assignee IDs. Respect priority, dependency order, sprint dates, capacity points, holidays, leave-adjusted member capacity, and proposed ownership. Mark work deferred when it cannot fit safely. Do not commit a sprint or approve any recommendation."""

STORIES_PER_BATCH = 10


@dataclass(frozen=True)
class SprintPlanningGeneration:
    batch: SprintPlanningBatch
    prompt_hash: str


async def generate_sprint_plan(db: AsyncSession, project_id: str, session_id: str, provider: LLMProvider) -> SprintPlanningGeneration:
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    sprints = (await db.execute(select(Sprint).where(Sprint.project_id == project_id).order_by(Sprint.start_date))).scalars().all()
    assignments = (await db.execute(select(AssignmentRecommendation).where(AssignmentRecommendation.session_id == session_id))).scalars().all()
    members = (await db.execute(select(TeamMember).where(TeamMember.project_id == project_id))).scalars().all()
    dependencies = (await db.execute(select(Dependency).where(Dependency.session_id == session_id))).scalars().all()
    if not stories or not sprints or any(item.story_points is None for item in stories):
        raise ValueError("Estimated stories and verified sprints are required for sprint planning")
    sprint_external = {item.external_id or item.id: item for item in sprints}
    member_external = {item.external_id or item.id: item for item in members}
    member_key_by_id = {item.id: key for key, item in member_external.items()}
    assignment_by_story = {
        item.item_stable_id: member_key_by_id.get(item.team_member_id)
        for item in assignments if item.item_stable_id.startswith("STORY-")
    }
    story_context = [{
        "stable_id": item.stable_id, "title": item.title, "story_points": item.story_points,
        "priority": item.priority, "recommended_assignee_id": assignment_by_story.get(item.stable_id),
    } for item in stories]
    sprint_context = [{
        "sprint_id": key, "name": item.name, "start_date": str(item.start_date),
        "end_date": str(item.end_date), "capacity_points": item.capacity_points,
        "already_committed_points": item.committed_points,
    } for key, item in sprint_external.items()]
    dependency_context = [{
        "source": item.source_stable_id, "target": item.target_stable_id,
        "type": item.dependency_type, "risk": item.risk,
    } for item in dependencies if item.source_stable_id.startswith("STORY-") and item.target_stable_id.startswith("STORY-")]
    shape = {"decisions": [{
        "story_stable_id": "STORY-001", "decision": "planned | deferred",
        "sprint_id": "SPR-001 or null", "assignee_id": "MEM-001 or null",
        "reason": "string", "confidence": 0.85,
    }]}
    expected_story_ids = {item.stable_id for item in stories}
    story_by_id = {item.stable_id: item for item in stories}
    sprint_order = {key: index for index, key in enumerate(sprint_external)}
    dependents = {stable_id: [] for stable_id in expected_story_ids}
    indegree = {stable_id: 0 for stable_id in expected_story_ids}
    for dependency in dependency_context:
        if dependency["source"] in indegree and dependency["target"] in indegree:
            dependents[dependency["target"]].append(dependency["source"])
            indegree[dependency["source"]] += 1
    ready = sorted(stable_id for stable_id, degree in indegree.items() if degree == 0)
    ordered_ids = []
    while ready:
        stable_id = ready.pop(0)
        ordered_ids.append(stable_id)
        for dependent in sorted(dependents[stable_id]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
                ready.sort()
    if len(ordered_ids) != len(stories):
        raise ValueError("Story dependencies contain a cycle and cannot be sprint planned")

    context_by_id = {item["stable_id"]: item for item in story_context}
    merged_decisions = []
    prompts = []
    loads: dict[str, int] = {}
    for index in range(0, len(ordered_ids), STORIES_PER_BATCH):
        batch_ids = ordered_ids[index:index + STORIES_PER_BATCH]
        local_ids = set(batch_ids)
        context = {
            "stories": [context_by_id[stable_id] for stable_id in batch_ids],
            "sprints": [{
                **item,
                "remaining_capacity_points": (
                    item["capacity_points"] - item["already_committed_points"] - loads.get(item["sprint_id"], 0)
                    if item["capacity_points"] is not None else None
                ),
            } for item in sprint_context],
            "dependencies": [item for item in dependency_context if item["source"] in local_ids],
            "prior_decisions": [item.model_dump(mode="json") for item in merged_decisions],
        }
        prompt = "Create a sprint recommendation using this exact shape: " + compact_json(shape) + "\n\nDATA:\n" + compact_json(context)
        prompts.append(prompt)
        validation_error = ""
        for _ in range(2):
            raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
            try:
                batch = SprintPlanningBatch.model_validate_json(raw)
            except ValidationError as error:
                validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + str(error)
                continue
            ids = [item.story_stable_id for item in batch.decisions]
            candidate_decisions = [*merged_decisions, *batch.decisions]
            decision_by_story = {item.story_stable_id: item for item in candidate_decisions}
            candidate_loads = dict(loads)
            for item in batch.decisions:
                if item.decision == "planned" and item.sprint_id in sprint_external:
                    candidate_loads[item.sprint_id] = candidate_loads.get(item.sprint_id, 0) + (story_by_id[item.story_stable_id].story_points or 0)
            valid = (
                set(ids) == local_ids and len(ids) == len(local_ids)
                and all(item.decision == "deferred" or (item.sprint_id in sprint_external and item.assignee_id in member_external) for item in batch.decisions)
                and all(
                    sprint_external[sprint_id].capacity_points is not None
                    and points + sprint_external[sprint_id].committed_points <= sprint_external[sprint_id].capacity_points
                    for sprint_id, points in candidate_loads.items()
                )
                and all(
                    dependency["source"] not in decision_by_story
                    or decision_by_story[dependency["source"]].decision == "deferred"
                    or (
                        dependency["target"] in decision_by_story
                        and decision_by_story[dependency["target"]].decision == "planned"
                        and sprint_order[decision_by_story[dependency["target"]].sprint_id]
                        <= sprint_order[decision_by_story[dependency["source"]].sprint_id]
                    )
                    for dependency in dependency_context
                )
            )
            if valid:
                merged_decisions.extend(batch.decisions)
                loads = candidate_loads
                break
            validation_error = "\nReturn each supplied story exactly once, use valid IDs, stay within remaining capacity, and respect prior dependency decisions."
        else:
            raise ValueError(f"LLM sprint planning batch {index // STORIES_PER_BATCH + 1} failed validation after retry")
    result = SprintPlanningBatch(decisions=merged_decisions)
    if {item.story_stable_id for item in result.decisions} != expected_story_ids:
        raise ValueError("Merged sprint plan does not cover every story")
    return SprintPlanningGeneration(result, hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest())


async def persist_sprint_plan(db: AsyncSession, project_id: str, session_id: str, batch: SprintPlanningBatch) -> list[SprintPlanDecision]:
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id))).scalars().all()
    sprints = (await db.execute(select(Sprint).where(Sprint.project_id == project_id))).scalars().all()
    members = (await db.execute(select(TeamMember).where(TeamMember.project_id == project_id))).scalars().all()
    story_by_id = {item.stable_id: item for item in stories}
    sprint_by_external = {item.external_id or item.id: item for item in sprints}
    member_by_external = {item.external_id or item.id: item for item in members}
    records = []
    for draft in batch.decisions:
        provenance = {
            field: ProvenanceValue(value=value, origin="calculated", confidence=draft.confidence, source_references=[], requires_review=True).model_dump(mode="json")
            for field, value in {"decision": draft.decision, "sprint_id": draft.sprint_id, "assignee_id": draft.assignee_id, "reason": draft.reason}.items()
        }
        record = SprintPlanDecision(
            project_id=project_id, session_id=session_id, story_id=story_by_id[draft.story_stable_id].id,
            sprint_id=sprint_by_external[draft.sprint_id].id if draft.sprint_id else None,
            assignee_id=member_by_external[draft.assignee_id].id if draft.assignee_id else None,
            decision=draft.decision, reason=draft.reason, confidence=draft.confidence,
            provenance_json=json.dumps(provenance), status="proposed",
        )
        db.add(record)
        records.append(record)
    await db.flush()
    return records


async def sprint_plan_to_dicts(db: AsyncSession, records: list[SprintPlanDecision]) -> list[dict[str, object]]:
    stories = (await db.execute(select(UserStory).where(UserStory.id.in_({item.story_id for item in records})))).scalars().all() if records else []
    sprint_ids = {item.sprint_id for item in records if item.sprint_id}
    assignee_ids = {item.assignee_id for item in records if item.assignee_id}
    sprints = (await db.execute(select(Sprint).where(Sprint.id.in_(sprint_ids)))).scalars().all() if sprint_ids else []
    members = (await db.execute(select(TeamMember).where(TeamMember.id.in_(assignee_ids)))).scalars().all() if assignee_ids else []
    story_by_id = {item.id: item for item in stories}
    sprint_by_id = {item.id: item for item in sprints}
    member_by_id = {item.id: item for item in members}
    return [{
        "id": item.id, "story_stable_id": story_by_id[item.story_id].stable_id,
        "story_title": story_by_id[item.story_id].title, "story_points": story_by_id[item.story_id].story_points,
        "decision": item.decision,
        "sprint_id": (sprint_by_id[item.sprint_id].external_id or item.sprint_id) if item.sprint_id else None,
        "sprint_name": sprint_by_id[item.sprint_id].name if item.sprint_id else None,
        "assignee_id": (member_by_id[item.assignee_id].external_id or item.assignee_id) if item.assignee_id else None,
        "assignee_name": member_by_id[item.assignee_id].name if item.assignee_id else None,
        "reason": item.reason, "confidence": item.confidence,
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in records]