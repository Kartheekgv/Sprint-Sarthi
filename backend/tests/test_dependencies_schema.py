import pytest
from pydantic import ValidationError

from app.schemas.dependencies import DependencyBatch, DependencyDraft


def test_dependency_contract_accepts_directed_edge():
    edge = DependencyDraft(
        source_stable_id="STORY-002", target_stable_id="STORY-001",
        dependency_type="requires", risk="high",
        explanation="The reporting story requires authentication to be available first.", confidence=0.9,
    )
    assert edge.target_stable_id == "STORY-001"


def test_dependency_contract_rejects_self_edge():
    with pytest.raises(ValidationError, match="cannot depend on itself"):
        DependencyDraft(
            source_stable_id="TASK-001", target_stable_id="TASK-001",
            dependency_type="blocks", risk="medium",
            explanation="This invalid edge points back to the same task.", confidence=0.8,
        )


def test_dependency_contract_rejects_duplicate_edge():
    edge = DependencyDraft(
        source_stable_id="TASK-002", target_stable_id="TASK-001",
        dependency_type="requires", risk="medium",
        explanation="The second task consumes output produced by the first task.", confidence=0.8,
    )
    with pytest.raises(ValidationError, match="must be unique"):
        DependencyBatch(dependencies=[edge, edge])