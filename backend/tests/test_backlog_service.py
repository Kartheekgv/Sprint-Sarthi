import json
from types import SimpleNamespace

import pytest

from app.services.backlog import DECOMPOSITIONS_PER_BATCH, generate_backlog


class _ScalarResult:
    def __init__(self, records):
        self._records = records

    def scalars(self):
        return self

    def all(self):
        return self._records


class _Database:
    def __init__(self, records):
        self._records = records

    async def execute(self, _statement):
        return _ScalarResult(self._records)


class _Provider:
    def __init__(self):
        self.calls = 0

    async def generate_text(self, prompt, _system_prompt):
        self.calls += 1
        payload = prompt.split("\n\nDECOMPOSITIONS:\n", maxsplit=1)[1]
        context, _ = json.JSONDecoder().raw_decode(payload)
        return json.dumps({
            "epics": [{
                "epic_key": "E1",
                "decomposition_ids": [item["decomposition_id"] for item in context],
                "title": f"Evidence batch {self.calls}",
                "description": "Groups related evidence into independently reviewable backlog work.",
                "business_value": "Delivers verified scope without inventing unsupported work.",
                "confidence": 0.9,
            }],
            "stories": [{
                "story_key": f"S{index}",
                "parent_epic_key": "E1",
                "decomposition_ids": [item["decomposition_id"]],
                "title": f"Implement evidence item {index}",
                "user_story": "As a stakeholder, I want the evidenced capability so that the requirement is delivered.",
                "description": "Implements only the capability described by the linked decomposition evidence.",
                "confidence": 0.9,
            } for index, item in enumerate(context, start=1)],
            "tasks": [{
                "task_key": f"T{index}",
                "parent_story_key": f"S{index}",
                "decomposition_ids": [item["decomposition_id"]],
                "title": f"Build evidence item {index}",
                "description": "Implement and verify the linked evidence-backed capability.",
                "task_type": "implementation",
                "confidence": 0.9,
            } for index, item in enumerate(context, start=1)],
        })


@pytest.mark.asyncio
async def test_generate_backlog_batches_100_evidence_items_without_key_collisions():
    decompositions = [SimpleNamespace(
        stable_id=f"DEC-{index:03d}",
        requirement_ids_json=json.dumps([f"REQ-{index:03d}"]),
        parent_capability="Capability",
        component_type="functional",
        title=f"Evidence {index}",
        description="A source-backed capability requiring implementation.",
        suggested_backlog_level="story",
        rationale="The source describes independently valuable behavior.",
    ) for index in range(1, 101)]
    provider = _Provider()

    generation = await generate_backlog(_Database(decompositions), "session-1", provider)

    assert provider.calls == 100 // DECOMPOSITIONS_PER_BATCH + 1
    assert len(generation.batch.epics) == provider.calls
    assert len(generation.batch.stories) == 100
    assert len(generation.batch.tasks) == 100
    assert len({item.story_key for item in generation.batch.stories}) == 100
    assert len({item.task_key for item in generation.batch.tasks}) == 100
    referenced_ids = {
        decomposition_id
        for collection in (generation.batch.epics, generation.batch.stories, generation.batch.tasks)
        for item in collection
        for decomposition_id in item.decomposition_ids
    }
    assert referenced_ids == {item.stable_id for item in decompositions}
