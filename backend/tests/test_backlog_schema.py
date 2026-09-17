import pytest
from pydantic import ValidationError

from app.schemas.backlog import BacklogBatch, EpicDraft, StoryDraft, TaskDraft


def _valid_batch() -> BacklogBatch:
    return BacklogBatch(
        epics=[EpicDraft(
            epic_key="E1", decomposition_ids=["DEC-001"], title="Request management",
            description="Manage requests throughout their business lifecycle.",
            business_value="Reduces manual coordination and processing delays.",
            confidence=0.9,
        )],
        stories=[StoryDraft(
            story_key="S1", parent_epic_key="E1", decomposition_ids=["DEC-002"],
            title="Submit a request", user_story="As a requester, I want to submit a request for review.",
            description="Capture and submit a complete request for downstream review.",
            confidence=0.88,
        )],
        tasks=[TaskDraft(
            task_key="T1", parent_story_key="S1", decomposition_ids=["DEC-003"],
            title="Build request form", description="Implement the request data-entry and submission flow.",
            task_type="implementation", confidence=0.86,
        )],
    )


def test_backlog_contract_accepts_complete_hierarchy():
    batch = _valid_batch()
    assert batch.tasks[0].parent_story_key == "S1"


def test_backlog_contract_rejects_orphan_story():
    with pytest.raises(ValidationError, match="reference an epic"):
        BacklogBatch(
            epics=_valid_batch().epics,
            stories=[_valid_batch().stories[0].model_copy(update={"parent_epic_key": "E2"})],
            tasks=_valid_batch().tasks,
        )


def test_backlog_contract_rejects_story_without_task():
    extra_story = _valid_batch().stories[0].model_copy(update={"story_key": "S2"})
    with pytest.raises(ValidationError, match="Every story must contain"):
        BacklogBatch(
            epics=_valid_batch().epics,
            stories=[*_valid_batch().stories, extra_story],
            tasks=_valid_batch().tasks,
        )