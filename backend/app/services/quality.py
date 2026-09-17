import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    AssignmentRecommendation, BoardHealthResult, Dependency, DuplicateCandidate, Epic,
    QualityResult, Sprint, SprintPlanDecision, Task, UserStory,
)


def _quality(item, item_type: str) -> tuple[dict[str, bool], list[str], int]:
    common = {
        "title_present": bool(item.title.strip()),
        "description_present": bool(item.description.strip()),
        "priority_set": item.priority in {"Critical", "High", "Medium", "Low"},
        "source_traceable": bool(json.loads(item.source_references_json)),
    }
    if item_type == "epic":
        specific = {
            "business_value_present": bool(item.business_value.strip()),
            "acceptance_criteria_present": bool(json.loads(item.acceptance_criteria or "[]")),
        }
    elif item_type == "story":
        specific = {
            "user_story_present": bool(item.user_story.strip()),
            "acceptance_criteria_present": bool(json.loads(item.acceptance_criteria or "[]")),
            "estimated": item.story_points in {1, 2, 3, 5, 8, 13},
        }
    else:
        specific = {
            "task_type_present": bool(item.task_type.strip()),
            "estimated": item.estimated_hours is not None and item.estimated_hours > 0,
        }
    checks = {**common, **specific}
    issues = [name.replace("_", " ") for name, passed in checks.items() if not passed]
    score = round(100 * sum(checks.values()) / len(checks))
    return checks, issues, score


async def run_quality_checks(db: AsyncSession, project_id: str, session_id: str) -> list[QualityResult]:
    collections = [
        ("epic", (await db.execute(select(Epic).where(Epic.session_id == session_id))).scalars().all()),
        ("story", (await db.execute(select(UserStory).where(UserStory.session_id == session_id))).scalars().all()),
        ("task", (await db.execute(select(Task).where(Task.session_id == session_id))).scalars().all()),
    ]
    results = []
    for item_type, items in collections:
        for item in items:
            checks, issues, score = _quality(item, item_type)
            record = QualityResult(
                project_id=project_id, session_id=session_id, item_id=item.stable_id,
                item_type=item_type, score=score,
                details_json=json.dumps({"passed": score >= 80, "issues": issues, "checks": checks}),
            )
            db.add(record)
            results.append(record)
    await db.flush()
    return results


def quality_to_dict(record: QualityResult) -> dict[str, object]:
    details = json.loads(record.details_json)
    return {"id": record.id, "item_id": record.item_id, "item_type": record.item_type, "score": record.score, **details}


async def run_board_health(db: AsyncSession, project_id: str, session_id: str) -> BoardHealthResult:
    quality = (await db.execute(select(QualityResult).where(QualityResult.session_id == session_id))).scalars().all()
    dependencies = (await db.execute(select(Dependency).where(Dependency.session_id == session_id))).scalars().all()
    duplicates = (await db.execute(select(DuplicateCandidate).where(DuplicateCandidate.session_id == session_id))).scalars().all()
    decisions = (await db.execute(select(SprintPlanDecision).where(SprintPlanDecision.session_id == session_id))).scalars().all()
    assignments = (await db.execute(select(AssignmentRecommendation).where(AssignmentRecommendation.session_id == session_id))).scalars().all()
    sprints = (await db.execute(select(Sprint).where(Sprint.project_id == project_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id))).scalars().all()
    story_by_id = {item.id: item for item in stories}
    sprint_by_id = {item.id: item for item in sprints}
    loads: dict[str, int] = {}
    for decision in decisions:
        if decision.decision == "planned" and decision.sprint_id:
            loads[decision.sprint_id] = loads.get(decision.sprint_id, 0) + (story_by_id[decision.story_id].story_points or 0)
    overloads = sum(
        1 for sprint_id, points in loads.items()
        if sprint_by_id[sprint_id].capacity_points is not None and points > sprint_by_id[sprint_id].capacity_points
    )
    high_utilization = sum(
        1 for sprint_id, points in loads.items()
        if sprint_by_id[sprint_id].capacity_points and points / sprint_by_id[sprint_id].capacity_points >= 0.9
    )
    low_quality = sum(item.score < 80 for item in quality)
    high_risk_dependencies = sum(item.risk in {"critical", "high"} for item in dependencies)
    deferred = sum(item.decision == "deferred" for item in decisions)
    unassigned = max(0, len(stories) - sum(item.item_stable_id.startswith("STORY-") for item in assignments))
    metrics = {
        "average_quality": round(sum(item.score for item in quality) / len(quality), 1) if quality else 0,
        "low_quality_items": low_quality, "duplicate_candidates": len(duplicates),
        "high_risk_dependencies": high_risk_dependencies, "deferred_stories": deferred,
        "overloaded_sprints": overloads, "high_utilization_sprints": high_utilization,
        "unassigned_stories": unassigned,
    }
    issues = []
    for count, message in (
        (low_quality, "Backlog items failed the quality threshold."),
        (len(duplicates), "Duplicate candidates require human disposition."),
        (high_risk_dependencies, "High-risk dependencies require mitigation."),
        (deferred, "Stories were deferred due to constraints."),
        (overloads, "Sprint capacity is exceeded."),
        (high_utilization, "Sprint utilization is at or above 90%."),
        (unassigned, "Stories have no proposed owner."),
    ):
        if count:
            issues.append(f"{count} {message}")
    score = max(0, 100 - low_quality * 10 - len(duplicates) * 5 - high_risk_dependencies * 8 - deferred * 5 - overloads * 25 - high_utilization * 5 - unassigned * 10)
    risk_level = "high" if score < 60 else "medium" if score < 80 else "low"
    record = BoardHealthResult(
        project_id=project_id, session_id=session_id, score=score, risk_level=risk_level,
        metrics_json=json.dumps(metrics), issues_json=json.dumps(issues), status="review_required",
    )
    db.add(record)
    await db.flush()
    return record


def board_health_to_dict(record: BoardHealthResult) -> dict[str, object]:
    return {
        "id": record.id, "score": record.score, "risk_level": record.risk_level,
        "metrics": json.loads(record.metrics_json), "issues": json.loads(record.issues_json),
        "status": record.status,
    }