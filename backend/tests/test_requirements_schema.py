import pytest
from pydantic import ValidationError

from app.schemas.requirements import RequirementDraft


def requirement_payload() -> dict[str, object]:
    return {
        "title": "Record approval audit events",
        "description": "The platform records every approval decision in an immutable audit history.",
        "category": "auditability",
        "requirement_status": "explicit",
        "actors": ["Approver"],
        "systems": ["Approval service"],
        "business_rules": [],
        "constraints": [],
        "assumptions": [],
        "priority": "Unknown",
        "rationale": "The source explicitly requires an approval audit history.",
        "acceptance_criteria": [],
        "source_references": ["SRC-0001"],
        "confidence": 0.93,
        "requires_clarification": True,
        "clarification_reasons": ["Audit retention period is missing."],
    }


def test_requirement_supports_full_agent_contract():
    requirement = RequirementDraft.model_validate(requirement_payload())
    assert requirement.category == "auditability"
    assert requirement.priority == "Unknown"


def test_requirement_rejects_unbounded_confidence():
    payload = requirement_payload()
    payload["confidence"] = 1.1
    with pytest.raises(ValidationError):
        RequirementDraft.model_validate(payload)