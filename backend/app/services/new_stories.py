import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Feature, Sprint, UserStory
from app.providers.base import LLMProvider
from app.schemas.duplicates import NewStoryAssessment, NewStoryCheckCreate
from app.services.prompting import compact_json


SYSTEM_PROMPT = """You are Sprint Sarthi's New Story Gate. Return JSON only and never markdown.
Compare the proposed story semantically against every supplied original story, not just exact wording. Classify it as duplicate when the same user outcome and scope already exist, clarification when key scope is ambiguous, or new only when it is genuinely distinct. For a duplicate, identify the equivalent story and do not suggest creation. For a new story, recommend only a supplied Feature and an appropriate supplied uncommitted Sprint; never re-sequence or alter committed Sprint work. Ask concise hard questions instead of assuming missing facts."""


@dataclass(frozen=True)
class NewStoryAssessmentResult:
    assessment: NewStoryAssessment
    prompt_hash: str


async def assess_new_story(
    db: AsyncSession,
    project_id: str,
    session_id: str,
    proposal: NewStoryCheckCreate,
    provider: LLMProvider,
) -> NewStoryAssessmentResult:
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    features = (await db.execute(select(Feature).where(Feature.session_id == session_id).order_by(Feature.stable_id))).scalars().all()
    sprints = (await db.execute(select(Sprint).where(Sprint.project_id == project_id).order_by(Sprint.start_date))).scalars().all()
    if not stories or not features:
        raise ValueError("Generate the original Feature and Story hierarchy before checking a new story")
    shape = {
        "classification": "duplicate | new | clarification",
        "equivalent_story_id": "STORY-001 or null",
        "suggested_feature_id": "FEATURE-001 or null",
        "suggested_sprint_id": "SPR-001 or null",
        "rationale": "string", "clarifying_questions": ["string"], "confidence": 0.9,
    }
    context = {
        "proposal": proposal.model_dump(mode="json"),
        "original_stories": [{"stable_id": item.stable_id, "title": item.title, "user_story": item.user_story, "description": item.description} for item in stories],
        "features": [{"stable_id": item.stable_id, "title": item.title, "description": item.description} for item in features],
        "sprints": [{"sprint_id": item.external_id or item.id, "name": item.name, "committed": item.committed, "start_date": str(item.start_date), "end_date": str(item.end_date), "remaining_capacity_points": (item.capacity_points or 0) - item.committed_points} for item in sprints],
    }
    prompt = "Assess the proposed story before creation using this exact shape: " + compact_json(shape) + "\n\nDATA:\n" + compact_json(context)
    story_ids = {item.stable_id for item in stories}
    feature_ids = {item.stable_id for item in features}
    sprint_ids = {item.external_id or item.id for item in sprints if not item.committed}
    validation_error = ""
    for _ in range(3):
        raw = await provider.generate_text(prompt + validation_error, SYSTEM_PROMPT)
        try:
            assessment = NewStoryAssessment.model_validate_json(raw)
        except ValidationError as error:
            validation_error = "\nCorrect these schema errors and return the full JSON again:\n" + str(error)
            continue
        valid = (
            (assessment.classification != "duplicate" or assessment.equivalent_story_id in story_ids)
            and (assessment.classification != "new" or assessment.suggested_feature_id in feature_ids)
            and (assessment.suggested_sprint_id is None or assessment.suggested_sprint_id in sprint_ids)
            and (assessment.classification != "clarification" or bool(assessment.clarifying_questions))
        )
        if valid:
            return NewStoryAssessmentResult(assessment, hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        validation_error = "\nUse only supplied IDs. New stories require a Feature; clarification requires at least one question; never suggest a committed Sprint."
    raise ValueError("New-story assessment failed validation after 3 attempts")
