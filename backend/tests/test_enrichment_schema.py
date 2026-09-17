import pytest
from pydantic import ValidationError

from app.schemas.enrichment import EpicEnrichment, StoryEnrichment


def test_enrichment_contract_accepts_testable_story_criteria():
    item = StoryEnrichment(
        stable_id="STORY-001",
        acceptance_criteria=["Given a valid identity, when login succeeds, then the dashboard opens."],
        priority="High",
        confidence=0.9,
    )
    assert item.priority == "High"


def test_enrichment_contract_rejects_unknown_priority():
    with pytest.raises(ValidationError):
        EpicEnrichment(
            stable_id="EPIC-001",
            business_value="Protect access to confidential project information.",
            priority="Urgent",
            acceptance_criteria=["Authorized users can access protected functions."],
            confidence=0.8,
        )