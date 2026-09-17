import pytest
from pydantic import ValidationError

from app.schemas.estimation import StoryEstimate, TaskEstimate


def test_estimation_contract_accepts_fibonacci_points_and_hours():
    story = StoryEstimate(
        stable_id="STORY-001", story_points=5,
        rationale="Moderate implementation complexity with one external integration.", confidence=0.8,
    )
    task = TaskEstimate(
        stable_id="TASK-001", estimated_hours=12,
        rationale="Implementation and focused automated tests require about twelve hours.", confidence=0.75,
    )
    assert story.story_points == 5
    assert task.estimated_hours == 12


def test_estimation_contract_rejects_non_fibonacci_points():
    with pytest.raises(ValidationError):
        StoryEstimate(
            stable_id="STORY-001", story_points=4,
            rationale="The estimate uses an unsupported point value.", confidence=0.8,
        )