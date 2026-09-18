import json

from app.services.prompting import compact_json, json_repair_prompt


def test_compact_json_preserves_data_with_less_prompt_text():
    value = {"items": [{"title": "Access control", "enabled": True}], "count": 1}

    encoded = compact_json(value)

    assert json.loads(encoded) == value
    assert len(encoded) < len(json.dumps(value))


def test_json_repair_prompt_does_not_repeat_large_source_context():
    original_prompt = "SOURCE EVIDENCE:\n" + ("architecture evidence " * 2000)

    repair = json_repair_prompt(
        '{"items":[{"source_id":"INVALID"}]}',
        "Use a supplied source ID",
        {"items": [{"source_id": "SRC-0001"}]},
        "Allowed source IDs: SRC-0001",
    )

    assert "architecture evidence" not in repair
    assert "PRIOR OUTPUT" in repair
    assert len(repair) < len(original_prompt) / 10