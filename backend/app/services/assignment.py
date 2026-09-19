import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    AssignmentRecommendation, Department, Holiday, Leave, Sprint, Task, TeamMember, UserStory,
)
from app.providers.base import LLMProvider
from app.services.prompting import compact_json
from app.services.capacity import capacity_by_member
from app.schemas.planning_data import AssignmentBatch, AssignmentDraft
from app.schemas.provenance import ProvenanceValue


SYSTEM_PROMPT = """You are Sprint Sarthi's Assignment Agent. Return JSON only and never markdown.
Recommend exactly one team member for every supplied story and task. Use only supplied member IDs. Match required work to demonstrated roles and skills. Use the supplied verified capacity snapshots as facts; never calculate capacity, working days, leave days, holidays, allocation, or utilization. Story assignments indicate ownership and must use null recommended_hours. Task recommended_hours must equal the supplied estimate. Do not schedule sprints or approve assignments. Every recommendation requires human review."""

STORIES_PER_BATCH = 5


@dataclass(frozen=True)
class AssignmentGeneration:
    batch: AssignmentBatch
    prompt_hash: str


def _deterministic_assignment(
    item_id: str,
    task_by_id: dict[str, Task],
    member_by_external: dict[str, TeamMember],
    capacity_by_external: dict[str, float],
    loads: dict[str, float],
) -> object:
    task = task_by_id.get(item_id)
    hours = float(task.estimated_hours or 0) if task else 0.0
    task_text = "" if task is None else f"{task.title} {task.description} {task.task_type}".lower()
    candidates = []
    for member_id, member in member_by_external.items():
        remaining = capacity_by_external.get(member_id, 0.0) - loads.get(member_id, 0.0)
        if task and remaining < hours:
            continue
        skills = [str(skill) for skill in json.loads(member.skills_json)]
        matches = sum(skill.lower() in task_text for skill in skills)
        candidates.append((matches, remaining, member_id, member))
    if not candidates:
        raise ValueError(f"Verified team capacity is insufficient for {item_id}")
    _, remaining, member_id, _ = max(candidates, key=lambda item: (item[0], item[1], item[2]))
    if task:
        loads[member_id] = loads.get(member_id, 0.0) + hours
    return {
        "item_stable_id": item_id,
        "team_member_id": member_id,
        "recommended_hours": task.estimated_hours if task else None,
        "match_score": 0.5 if task else 0.6,
        "reason": (
            f"Deterministic recommendation using verified capacity; {remaining:g} hours remain. "
            "Human review required."
        ),
        "confidence": 0.5,
    }


def _rebalance_for_capacity(
    batch: AssignmentBatch,
    task_by_id: dict[str, Task],
    member_by_external: dict[str, TeamMember],
    capacity_by_external: dict[str, float] | None = None,
) -> AssignmentBatch | None:
    capacity_by_external = capacity_by_external or {
        member_id: float(member.capacity_hours or 0)
        for member_id, member in member_by_external.items()
    }
    loads = {member_id: 0.0 for member_id in member_by_external}
    replacements: dict[str, object] = {}
    task_assignments = sorted(
        (item for item in batch.assignments if item.item_stable_id in task_by_id),
        key=lambda item: task_by_id[item.item_stable_id].estimated_hours or 0,
        reverse=True,
    )
    for item in task_assignments:
        task = task_by_id[item.item_stable_id]
        hours = float(task.estimated_hours or 0)
        candidates = []
        task_text = f"{task.title} {task.description} {task.task_type}".lower()
        for member_id, member in member_by_external.items():
            capacity = capacity_by_external.get(member_id, 0.0)
            if loads[member_id] + hours > capacity:
                continue
            skills = [str(skill) for skill in json.loads(member.skills_json)]
            matched_skills = [skill for skill in skills if skill.lower() in task_text]
            remaining = capacity - loads[member_id]
            candidates.append((len(matched_skills), member_id == item.team_member_id, remaining, member_id, member, matched_skills))
        if not candidates:
            return None
        _, _, remaining, member_id, member, matched_skills = max(candidates, key=lambda candidate: candidate[:3])
        loads[member_id] += hours
        if member_id != item.team_member_id:
            basis = ", ".join(matched_skills) if matched_skills else f"{remaining:g} verified available hours"
            replacements[item.item_stable_id] = item.model_copy(update={
                "team_member_id": member_id,
                "match_score": min(item.match_score, 0.75),
                "reason": f"Capacity-adjusted recommendation for {member.name} based on {basis}; human review required.",
                "confidence": min(item.confidence, 0.75),
            })
    return AssignmentBatch(assignments=[
        replacements.get(item.item_stable_id, item) for item in batch.assignments
    ])


async def _generate_assignments(
    db: AsyncSession,
    project_id: str,
    session_id: str,
    provider: LLMProvider,
) -> AssignmentGeneration:
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id).order_by(Task.stable_id))).scalars().all()
    members = (await db.execute(select(TeamMember).where(TeamMember.project_id == project_id).order_by(TeamMember.name))).scalars().all()
    departments = (await db.execute(select(Department).where(Department.project_id == project_id))).scalars().all()
    sprints = (await db.execute(select(Sprint).where(Sprint.project_id == project_id).order_by(Sprint.start_date))).scalars().all()
    holidays = (await db.execute(select(Holiday).where(Holiday.project_id == project_id).order_by(Holiday.day))).scalars().all()
    leaves = (await db.execute(select(Leave).where(Leave.project_id == project_id).order_by(Leave.start_date))).scalars().all()
    if not stories or not tasks or not members:
        raise ValueError("Stories, tasks, and verified team members are required for assignment")
    department_by_id = {item.id: item.name for item in departments}
    member_external_by_id = {item.id: item.external_id or item.id for item in members}
    verified_capacity, capacity_snapshots = capacity_by_member(members, sprints, holidays, leaves)
    story_context = [{
            "stable_id": item.stable_id, "title": item.title, "description": item.description,
            "story_points": item.story_points, "priority": item.priority,
        } for item in stories]
    story_stable_by_id = {item.id: item.stable_id for item in stories}
    task_context = [{
            "stable_id": item.stable_id, "title": item.title, "description": item.description,
            "story_id": story_stable_by_id[item.story_id], "task_type": item.task_type,
            "estimated_hours": item.estimated_hours, "priority": item.priority,
        } for item in tasks]
    shared_context = {
        "team_members": [{
            "team_member_id": item.external_id or item.id, "name": item.name, "role": item.role,
            "department": department_by_id.get(item.department_id, ""), "skills": json.loads(item.skills_json),
            "verified_capacity_hours": verified_capacity.get(item.external_id or item.id, 0.0),
            "location": item.location,
        } for item in members],
        "sprints": [{"name": item.name, "start_date": str(item.start_date), "end_date": str(item.end_date)} for item in sprints],
        "holidays": [{"date": str(item.day), "name": item.name, "location": item.location} for item in holidays],
        "leaves": [{
            "team_member_id": member_external_by_id[item.team_member_id],
            "start_date": str(item.start_date), "end_date": str(item.end_date), "reason": item.reason,
        } for item in leaves],
        "capacity_snapshots": [item.model_dump(mode="json") for item in capacity_snapshots],
    }
    shape = {"assignments": [{
        "item_stable_id": "TASK-001", "team_member_id": "MEM-001",
        "recommended_hours": 12, "match_score": 0.9, "reason": "string", "confidence": 0.85,
    }]}
    expected_ids = {item.stable_id for item in [*stories, *tasks]}
    member_by_external = {item.external_id or item.id: item for item in members}
    task_by_id = {item.stable_id: item for item in tasks}
    merged_assignments = []
    prompts = []
    for index in range(0, len(story_context), STORIES_PER_BATCH):
        batch_stories = story_context[index:index + STORIES_PER_BATCH]
        story_ids = {item["stable_id"] for item in batch_stories}
        context = {
            "stories": batch_stories,
            "tasks": [item for item in task_context if item["story_id"] in story_ids],
            **shared_context,
        }
        prompt = "Recommend assignments using this exact shape: " + compact_json(shape) + "\n\nPLANNING DATA:\n" + compact_json(context)
        prompts.append(prompt)
        local_ids = story_ids | {item["stable_id"] for item in context["tasks"]}
        validation_error = ""
        final_error = "unknown assignment mismatch"
        recovered: dict[str, AssignmentDraft] = {}
        batch_completed = False
        for _ in range(3):
            try:
                raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
            except Exception as error:
                final_error = str(error)
                break
            try:
                batch = AssignmentBatch.model_validate_json(raw)
            except ValidationError as error:
                final_error = "; ".join(
                    f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}"
                    for issue in error.errors(include_url=False, include_input=False)
                )
                validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + final_error
                continue
            item_ids = [item.item_stable_id for item in batch.assignments]
            issues = []
            if set(item_ids) != local_ids or len(item_ids) != len(local_ids):
                issues.append("return every supplied item ID exactly once")
            if any(item.team_member_id not in member_by_external for item in batch.assignments):
                issues.append("use only supplied member IDs")
            for item in batch.assignments:
                if item.item_stable_id in task_by_id and item.recommended_hours != task_by_id[item.item_stable_id].estimated_hours:
                    issues.append(f"{item.item_stable_id} must use {task_by_id[item.item_stable_id].estimated_hours} hours")
                elif item.item_stable_id in story_ids and item.recommended_hours is not None:
                    issues.append(f"{item.item_stable_id} must use null hours")
            if not issues:
                merged_assignments.extend(batch.assignments)
                batch_completed = True
                break
            final_error = "; ".join(issues)
            validation_error = "\nCorrect every validation error and return the full batch:\n" + final_error
            for item in batch.assignments:
                if item.item_stable_id not in local_ids or item.item_stable_id in recovered:
                    continue
                if item.team_member_id not in member_by_external:
                    continue
                if item.item_stable_id in task_by_id:
                    if item.recommended_hours != task_by_id[item.item_stable_id].estimated_hours:
                        continue
                elif item.recommended_hours is not None:
                    continue
                recovered[item.item_stable_id] = item
        if not batch_completed:
            fallback_loads: dict[str, float] = {}
            for item in recovered.values():
                if item.item_stable_id in task_by_id:
                    fallback_loads[item.team_member_id] = fallback_loads.get(item.team_member_id, 0.0) + (
                        item.recommended_hours or 0
                    )
            for missing_id in sorted(local_ids - recovered.keys()):
                recovered[missing_id] = AssignmentDraft.model_validate(_deterministic_assignment(
                    missing_id,
                    task_by_id,
                    member_by_external,
                    verified_capacity,
                    fallback_loads,
                ))
            merged_assignments.extend(recovered.values())
    merged = AssignmentBatch(assignments=merged_assignments)
    if {item.item_stable_id for item in merged.assignments} != expected_ids:
        raise ValueError("Merged assignment output does not cover the complete backlog")
    loads: dict[str, float] = {}
    for item in merged.assignments:
        if item.item_stable_id in task_by_id:
            loads[item.team_member_id] = loads.get(item.team_member_id, 0) + (item.recommended_hours or 0)
    overloaded = any(hours > verified_capacity.get(member_id, 0.0) for member_id, hours in loads.items())
    if overloaded:
        merged = _rebalance_for_capacity(merged, task_by_id, member_by_external, verified_capacity)
        if merged is None:
            raise ValueError("Verified team capacity is insufficient for the estimated task hours")
    return AssignmentGeneration(merged, hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest())


class _DeterministicAssignmentProvider:
    async def generate_text(self, _prompt: str, _system_prompt: str | None = None) -> str:
        return '{"assignments": []}'


async def generate_assignments(
    db: AsyncSession,
    project_id: str,
    session_id: str,
    provider: LLMProvider,
) -> AssignmentGeneration:
    try:
        return await _generate_assignments(db, project_id, session_id, provider)
    except Exception:
        return await _generate_assignments(
            db, project_id, session_id, _DeterministicAssignmentProvider()
        )


async def persist_assignments(
    db: AsyncSession,
    project_id: str,
    session_id: str,
    batch: AssignmentBatch,
) -> list[AssignmentRecommendation]:
    members = (await db.execute(select(TeamMember).where(TeamMember.project_id == project_id))).scalars().all()
    member_by_external = {item.external_id or item.id: item for item in members}
    records: list[AssignmentRecommendation] = []
    for draft in batch.assignments:
        member = member_by_external[draft.team_member_id]
        provenance = {
            field_name: ProvenanceValue(
                value=value, origin="inferred", confidence=draft.confidence,
                source_references=[], requires_review=True,
            ).model_dump(mode="json")
            for field_name, value in {
                "team_member_id": draft.team_member_id, "recommended_hours": draft.recommended_hours,
                "match_score": draft.match_score, "reason": draft.reason,
            }.items()
        }
        provenance["team_member_source"] = json.loads(member.provenance_json)
        record = AssignmentRecommendation(
            project_id=project_id, session_id=session_id, item_stable_id=draft.item_stable_id,
            team_member_id=member.id, recommended_hours=draft.recommended_hours,
            match_score=draft.match_score, reason=draft.reason, confidence=draft.confidence,
            provenance_json=json.dumps(provenance), status="proposed",
        )
        db.add(record)
        records.append(record)
    await db.flush()
    return records


async def assignments_to_dicts(
    db: AsyncSession, records: list[AssignmentRecommendation]
) -> list[dict[str, object]]:
    member_ids = {item.team_member_id for item in records}
    members = (await db.execute(select(TeamMember).where(TeamMember.id.in_(member_ids)))).scalars().all() if member_ids else []
    department_ids = {item.department_id for item in members if item.department_id}
    departments = (await db.execute(select(Department).where(Department.id.in_(department_ids)))).scalars().all() if department_ids else []
    member_by_id = {item.id: item for item in members}
    department_by_id = {item.id: item.name for item in departments}
    return [{
        "id": item.id, "item_stable_id": item.item_stable_id,
        "team_member_id": member_by_id[item.team_member_id].external_id or item.team_member_id,
        "team_member_name": member_by_id[item.team_member_id].name,
        "role": member_by_id[item.team_member_id].role,
        "department": department_by_id.get(member_by_id[item.team_member_id].department_id, ""),
        "recommended_hours": item.recommended_hours, "match_score": item.match_score,
        "reason": item.reason, "confidence": item.confidence,
        "provenance": json.loads(item.provenance_json), "status": item.status,
    } for item in records]