from app.schemas.duplicates import DuplicateBatch
from app.services.duplicates import _filter_duplicate_candidates


def test_duplicate_batch_normalizes_reversed_pairs():
    batch = DuplicateBatch.model_validate({"candidates": [{
        "source_stable_id": "STORY-026",
        "target_stable_id": "STORY-022",
        "similarity": 0.91,
        "rationale": "Both stories describe the same user-facing workflow.",
        "recommendation": "clarify",
        "confidence": 0.86,
    }]})

    assert batch.candidates[0].source_stable_id == "STORY-022"
    assert batch.candidates[0].target_stable_id == "STORY-026"


def test_duplicate_filter_discards_cross_level_relationships():
    batch = DuplicateBatch.model_validate({"candidates": [
        {
            "source_stable_id": "STORY-027", "target_stable_id": "TASK-047",
            "similarity": 0.95, "rationale": "The task implements its parent story workflow.",
            "recommendation": "keep_both", "confidence": 0.9,
        },
        {
            "source_stable_id": "STORY-027", "target_stable_id": "STORY-028",
            "similarity": 0.88, "rationale": "Both stories describe the same user outcome.",
            "recommendation": "clarify", "confidence": 0.8,
        },
    ]})
    known_ids = {"STORY-027", "STORY-028", "TASK-047"}

    filtered, unknown_ids = _filter_duplicate_candidates(
        batch, known_ids, {item: item.split("-")[0] for item in known_ids}
    )

    assert unknown_ids == []
    assert len(filtered.candidates) == 1
    assert filtered.candidates[0].target_stable_id == "STORY-028"