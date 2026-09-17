import pytest
from pydantic import ValidationError

from app.schemas.clarifications import ClarificationDraft


def clarification_payload() -> dict[str, object]:
    return {
        "requirement_id": "REQ-001",
        "question": "Which role may approve an access request?",
        "reason": "The requirement describes approval but does not identify an approver.",
        "severity": "critical",
        "missing_field": "approver_role",
        "recommended_answer_type": "single_select",
        "options": ["Manager", "System owner", "Security administrator"],
        "recommended_option": "System owner",
        "allow_custom_answer": True,
        "blocking": True,
        "source_references": ["SRC-0001"],
    }


def test_critical_clarification_is_blocking():
    clarification = ClarificationDraft.model_validate(clarification_payload())
    assert clarification.requirement_id == "REQ-001"
    assert clarification.blocking is True


def test_critical_clarification_cannot_be_nonblocking():
    payload = clarification_payload()
    payload["blocking"] = False
    with pytest.raises(ValidationError):
        ClarificationDraft.model_validate(payload)