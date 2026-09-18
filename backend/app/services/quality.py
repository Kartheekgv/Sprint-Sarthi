import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import (
    AssignmentRecommendation, BoardHealthResult, Dependency, DuplicateCandidate, Epic, Feature,
    QualityClarification, QualityResult, Sprint, SprintPlanDecision, Task, UserStory,
)


QUALITY_THRESHOLD = 85


def calculate_board_health_score(
    *, average_quality: float, quality_items: int, duplicate_candidates: int,
    dependencies: int, high_risk_dependencies: int, stories: int,
    deferred_stories: int, overloaded_sprints: int, sprints: int,
    unassigned_stories: int,
) -> tuple[int, str, dict[str, float]]:
    quality_rate = max(0.0, min(1.0, average_quality / 100)) if quality_items else 0.0
    duplicate_rate = min(1.0, duplicate_candidates / max(quality_items, 1))
    dependency_risk_rate = min(1.0, high_risk_dependencies / max(dependencies, 1))
    deferred_rate = min(1.0, deferred_stories / max(stories, 1))
    overload_rate = min(1.0, overloaded_sprints / max(sprints, 1))
    ownership_gap_rate = min(1.0, unassigned_stories / max(stories, 1))
    components = {
        "quality": round(35 * quality_rate, 1),
        "duplicate_readiness": round(10 * (1 - duplicate_rate), 1),
        "dependency_readiness": round(15 * (1 - dependency_risk_rate), 1),
        "delivery_feasibility": round(30 * max(0.0, 1 - deferred_rate - overload_rate), 1),
        "ownership_coverage": round(10 * (1 - ownership_gap_rate), 1),
    }
    score = round(sum(components.values()))
    risk_level = "high" if score < 60 else "medium" if score < 90 else "low"
    return score, risk_level, components


def _quality(item, item_type: str) -> tuple[dict[str, bool], list[str], int]:
    common = {
        "title_present": bool(item.title.strip()),
        "description_present": bool(item.description.strip()),
        "source_traceable": bool(json.loads(item.source_references_json)),
    }
    if item_type == "epic":
        specific = {
            "priority_set": item.priority in {"Critical", "High", "Medium", "Low"},
            "business_value_present": bool(item.business_value.strip()),
            "acceptance_criteria_present": bool(json.loads(item.acceptance_criteria or "[]")),
        }
    elif item_type == "feature":
        specific = {"business_value_present": bool(item.business_value.strip())}
    elif item_type == "story":
        specific = {
            "priority_set": item.priority in {"Critical", "High", "Medium", "Low"},
            "user_story_present": bool(item.user_story.strip()),
            "acceptance_criteria_present": bool(json.loads(item.acceptance_criteria or "[]")),
            "estimated": item.story_points in {1, 2, 3, 5, 8, 13},
            "definition_of_done_present": bool(json.loads(item.definition_of_done_json or "[]")),
        }
    else:
        specific = {
            "priority_set": item.priority in {"Critical", "High", "Medium", "Low"},
            "task_type_present": bool(item.task_type.strip()),
            "work_category_present": item.work_category in {"functional", "qa", "enabler", "infrastructure", "security", "compliance", "release"},
            "acceptance_criteria_present": bool(json.loads(item.acceptance_criteria_json or "[]")),
            "definition_of_done_present": bool(json.loads(item.definition_of_done_json or "[]")),
            "estimated": item.estimated_hours is not None and item.estimated_hours > 0,
        }
    checks = {**common, **specific}
    issues = [name.replace("_", " ") for name, passed in checks.items() if not passed]
    score = round(100 * sum(checks.values()) / len(checks))
    return checks, issues, score


async def run_quality_checks(db: AsyncSession, project_id: str, session_id: str) -> list[QualityResult]:
    collections = [
        ("epic", (await db.execute(select(Epic).where(Epic.session_id == session_id))).scalars().all()),
        ("feature", (await db.execute(select(Feature).where(Feature.session_id == session_id))).scalars().all()),
        ("story", (await db.execute(select(UserStory).where(UserStory.session_id == session_id, UserStory.status != "discarded"))).scalars().all()),
        ("task", (await db.execute(select(Task).where(Task.session_id == session_id, Task.status != "discarded"))).scalars().all()),
    ]
    results = []
    for item_type, items in collections:
        for item in items:
            checks, issues, score = _quality(item, item_type)
            record = QualityResult(
                project_id=project_id, session_id=session_id, item_id=item.stable_id,
                item_type=item_type, score=score,
                details_json=json.dumps({
                    "passed": score >= QUALITY_THRESHOLD,
                    "issues": issues,
                    "failed_fields": [name for name, passed in checks.items() if not passed],
                    "checks": checks,
                }),
            )
            db.add(record)
            results.append(record)
    await db.flush()
    return results


async def create_quality_clarifications(
    db: AsyncSession,
    session_id: str,
    results: list[QualityResult],
) -> list[QualityClarification]:
    records = []
    for result in results:
        if result.score >= QUALITY_THRESHOLD:
            continue
        details = json.loads(result.details_json)
        fields = details["failed_fields"]
        question = (
            f"{result.item_id} scored {result.score}%, below the {QUALITY_THRESHOLD}% readiness threshold. "
            f"Please provide explicit values for: {', '.join(field.replace('_', ' ') for field in fields)}."
        )
        record = await db.scalar(select(QualityClarification).where(
            QualityClarification.session_id == session_id,
            QualityClarification.item_id == result.item_id,
        ))
        if record is None:
            record = QualityClarification(
                session_id=session_id, item_id=result.item_id, item_type=result.item_type,
                missing_fields_json=json.dumps(fields), question=question,
            )
            db.add(record)
        else:
            record.missing_fields_json = json.dumps(fields)
            record.question = question
            record.status = "pending"
        records.append(record)
    await db.flush()
    return records


def quality_clarification_to_dict(record: QualityClarification) -> dict[str, object]:
    return {
        "id": record.id, "session_id": record.session_id, "item_id": record.item_id,
        "item_type": record.item_type, "missing_fields": json.loads(record.missing_fields_json),
        "question": record.question, "answer": json.loads(record.answer_json or "{}"),
        "status": record.status, "created_at": record.created_at,
    }


def apply_quality_clarification(item, item_type: str, missing_fields: list[str], values: dict[str, object]) -> None:
    field_by_check = {
        "title_present": "title", "description_present": "description", "priority_set": "priority",
        "source_traceable": "source_references", "business_value_present": "business_value",
        "user_story_present": "user_story", "acceptance_criteria_present": "acceptance_criteria",
        "definition_of_done_present": "definition_of_done", "task_type_present": "task_type",
        "work_category_present": "work_category",
        "estimated": "story_points" if item_type == "story" else "estimated_hours",
    }
    required = {field_by_check[field] for field in missing_fields}
    missing_answers = sorted(required - values.keys())
    if missing_answers:
        raise ValueError("Missing explicit answers for: " + ", ".join(missing_answers))
    for field in required:
        value = values[field]
        if field in {"title", "description", "business_value", "user_story"}:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be non-empty text")
            setattr(item, field, value.strip())
        elif field == "priority":
            if value not in {"Critical", "High", "Medium", "Low"}:
                raise ValueError("priority must be Critical, High, Medium, or Low")
            item.priority = value
        elif field in {"source_references", "acceptance_criteria", "definition_of_done"}:
            if not isinstance(value, list) or not value or not all(isinstance(entry, str) and entry.strip() for entry in value):
                raise ValueError(f"{field} must contain at least one non-empty value")
            column = {
                "source_references": "source_references_json",
                "acceptance_criteria": "acceptance_criteria_json" if item_type == "task" else "acceptance_criteria",
                "definition_of_done": "definition_of_done_json",
            }[field]
            setattr(item, column, json.dumps([entry.strip() for entry in value]))
        elif field == "task_type":
            if value not in {"implementation", "testing", "documentation", "analysis", "configuration"}:
                raise ValueError("task_type is invalid")
            item.task_type = value
        elif field == "work_category":
            if value not in {"functional", "qa", "enabler", "infrastructure", "security", "compliance", "release"}:
                raise ValueError("work_category is invalid")
            item.work_category = value
        elif field == "story_points":
            if value not in {1, 2, 3, 5, 8, 13}:
                raise ValueError("story_points must use 1, 2, 3, 5, 8, or 13")
            item.story_points = value
        elif field == "estimated_hours":
            if not isinstance(value, (int, float)) or value <= 0 or value > 200:
                raise ValueError("estimated_hours must be greater than 0 and no more than 200")
            item.estimated_hours = float(value)


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
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id, UserStory.status != "discarded"))).scalars().all()
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
    low_quality = sum(item.score < QUALITY_THRESHOLD for item in quality)
    high_risk_dependencies = sum(item.risk in {"critical", "high"} for item in dependencies)
    deferred = sum(item.decision == "deferred" for item in decisions)
    unassigned = max(0, len(stories) - sum(item.item_stable_id.startswith("STORY-") for item in assignments))
    metrics = {
        "average_quality": round(sum(item.score for item in quality) / len(quality), 1) if quality else 0,
        "quality_items": len(quality), "stories": len(stories), "dependencies": len(dependencies),
        "sprints": len(sprints),
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
    score, risk_level, components = calculate_board_health_score(
        average_quality=metrics["average_quality"], quality_items=len(quality),
        duplicate_candidates=len(duplicates), dependencies=len(dependencies),
        high_risk_dependencies=high_risk_dependencies, stories=len(stories),
        deferred_stories=deferred, overloaded_sprints=overloads, sprints=len(sprints),
        unassigned_stories=unassigned,
    )
    metrics.update({f"{name}_score": value for name, value in components.items()})
    record = await db.scalar(select(BoardHealthResult).where(BoardHealthResult.session_id == session_id))
    if record is None:
        record = BoardHealthResult(project_id=project_id, session_id=session_id)
        db.add(record)
    record.score = score
    record.risk_level = risk_level
    record.metrics_json = json.dumps(metrics)
    record.issues_json = json.dumps(issues)
    record.status = "review_required"
    await db.flush()
    return record


def board_health_to_dict(record: BoardHealthResult) -> dict[str, object]:
    return {
        "id": record.id, "score": record.score, "risk_level": record.risk_level,
        "metrics": json.loads(record.metrics_json), "issues": json.loads(record.issues_json),
        "status": record.status,
    }


def apply_quality_clarification(item, item_type: str, missing_fields: list[str], values: dict[str, object]) -> None:
    field_by_check = {
        "title_present": "title", "description_present": "description", "priority_set": "priority",
        "source_traceable": "source_references", "business_value_present": "business_value",
        "user_story_present": "user_story", "acceptance_criteria_present": "acceptance_criteria",
        "definition_of_done_present": "definition_of_done", "task_type_present": "task_type",
        "work_category_present": "work_category",
        "estimated": "story_points" if item_type == "story" else "estimated_hours",
    }
    required = {field_by_check[field] for field in missing_fields}
    missing_answers = sorted(required - values.keys())
    if missing_answers:
        raise ValueError("Missing explicit answers for: " + ", ".join(missing_answers))
    for field in required:
        value = values[field]
        if field in {"title", "description", "business_value", "user_story"}:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be non-empty text")
            setattr(item, field, value.strip())
        elif field == "priority":
            if value not in {"Critical", "High", "Medium", "Low"}:
                raise ValueError("priority must be Critical, High, Medium, or Low")
            item.priority = value
        elif field in {"source_references", "acceptance_criteria", "definition_of_done"}:
            if not isinstance(value, list) or not value or not all(isinstance(entry, str) and entry.strip() for entry in value):
                raise ValueError(f"{field} must contain at least one non-empty value")
            column = {
                "source_references": "source_references_json",
                "acceptance_criteria": "acceptance_criteria_json" if item_type == "task" else "acceptance_criteria",
                "definition_of_done": "definition_of_done_json",
            }[field]
            setattr(item, column, json.dumps([entry.strip() for entry in value]))
        elif field == "task_type":
            if value not in {"implementation", "testing", "documentation", "analysis", "configuration"}:
                raise ValueError("task_type is invalid")
            item.task_type = value
        elif field == "work_category":
            if value not in {"functional", "qa", "enabler", "infrastructure", "security", "compliance", "release"}:
                raise ValueError("work_category is invalid")
            item.work_category = value
        elif field == "story_points":
            if value not in {1, 2, 3, 5, 8, 13}:
                raise ValueError("story_points must use 1, 2, 3, 5, 8, or 13")
            item.story_points = value
        elif field == "estimated_hours":
            if not isinstance(value, (int, float)) or value <= 0 or value > 200:
                raise ValueError("estimated_hours must be greater than 0 and no more than 200")
            item.estimated_hours = float(value)