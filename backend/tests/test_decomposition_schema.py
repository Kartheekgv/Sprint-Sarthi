import pytest
from pydantic import ValidationError

from app.schemas.decomposition import DecompositionDraft


def test_decomposition_contract_accepts_business_capability():
    draft = DecompositionDraft(
        requirement_ids=["REQ-001"],
        parent_capability="Request approval",
        component_type="business_capability",
        title="Approval workflow",
        description="Manage approval decisions for submitted requests.",
        suggested_backlog_level="epic",
        rationale="The requirement describes a multi-step business outcome.",
        confidence=0.9,
    )
    assert draft.suggested_backlog_level == "epic"


def test_decomposition_contract_rejects_invalid_level():
    with pytest.raises(ValidationError):
        DecompositionDraft(
            requirement_ids=["REQ-001"], parent_capability="Approval",
            component_type="feature", title="Approval workflow",
            description="Manage approval decisions for submitted requests.",
            suggested_backlog_level="initiative", rationale="Too broad for one story.", confidence=0.8,
        )