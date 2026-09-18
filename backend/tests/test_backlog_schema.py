import pytest
from pydantic import ValidationError

from app.schemas.backlog import BacklogBatch, EpicDraft, FeatureDraft, StoryDraft, TaskDraft


def _valid_batch() -> BacklogBatch:
    return BacklogBatch(
        epics=[EpicDraft(
            epic_key="E1", decomposition_ids=["DEC-001"], title="Request management",
            description="Manage requests throughout their business lifecycle.",
            architecture_layer="Application services",
            business_value="Reduces manual coordination and processing delays.",
            confidence=0.9,
        )],
        features=[FeatureDraft(
            feature_key="F1", parent_epic_key="E1", decomposition_ids=["DEC-001"],
            title="Request submission", description="Provide the complete request submission capability.",
            business_value="Enables users to submit actionable requests.", confidence=0.89,
        )],
        stories=[StoryDraft(
            story_key="S1", parent_feature_key="F1", decomposition_ids=["DEC-002"],
            title="Submit a request", user_story="As a requester, I want to submit a request for review.",
            description="Capture and submit a complete request for downstream review.",
            definition_of_done=["Automated tests pass and acceptance criteria are verified."],
            confidence=0.88,
        )],
        tasks=[TaskDraft(
            task_key="T1", parent_story_key="S1", decomposition_ids=["DEC-003"],
            title="Build request form", description="Implement the request data-entry and submission flow.",
            task_type="implementation", work_category="functional",
            acceptance_criteria=["The form submits a complete valid request."],
            definition_of_done=["Code review and automated tests are complete."], confidence=0.86,
        )],
    )


def test_backlog_contract_accepts_complete_hierarchy():
    batch = _valid_batch()
    assert batch.tasks[0].parent_story_key == "S1"


def test_backlog_contract_rejects_orphan_story():
    with pytest.raises(ValidationError, match="reference a feature"):
        BacklogBatch(
            epics=_valid_batch().epics,
            features=_valid_batch().features,
            stories=[_valid_batch().stories[0].model_copy(update={"parent_feature_key": "F2"})],
            tasks=_valid_batch().tasks,
        )


def test_backlog_contract_rejects_story_without_task():
    extra_story = _valid_batch().stories[0].model_copy(update={"story_key": "S2"})
    with pytest.raises(ValidationError, match="Every story must contain"):
        BacklogBatch(
            epics=_valid_batch().epics,
            features=_valid_batch().features,
            stories=[*_valid_batch().stories, extra_story],
            tasks=_valid_batch().tasks,
        )