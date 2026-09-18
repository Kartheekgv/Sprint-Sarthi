import json
from types import SimpleNamespace

import pytest

from app.schemas.backlog import BacklogBatch
from app.services.backlog import DECOMPOSITIONS_PER_BATCH, _fallback_backlog_batch, _prune_orphan_hierarchy, generate_backlog


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
                "architecture_layer": "Application services",
                "business_value": "Delivers verified scope without inventing unsupported work.",
                "confidence": 0.9,
            }],
            "features": [
                {
                    "feature_key": f"F{index}",
                    "parent_epic_key": "E1",
                    "decomposition_ids": [item["decomposition_id"]],
                    "title": f"Evidence feature {index}",
                    "description": "Groups independently deliverable behavior for this evidence item.",
                    "business_value": "Provides a traceable increment of the architecture.",
                    "confidence": 0.9,
                } for index, item in enumerate(context, start=1)
            ],
            "stories": [{
                "story_key": f"S{index}",
                "parent_feature_key": f"F{index}",
                "decomposition_ids": [item["decomposition_id"]],
                "title": f"Implement evidence item {index}",
                "user_story": "As a stakeholder, I want the evidenced capability so that the requirement is delivered.",
                "description": "Implements only the capability described by the linked decomposition evidence.",
                "definition_of_done": ["Acceptance criteria pass and evidence is retained."],
                "confidence": 0.9,
            } for index, item in enumerate(context, start=1)],
            "tasks": [{
                "task_key": f"T{index}",
                "parent_story_key": f"S{index}",
                "decomposition_ids": [item["decomposition_id"]],
                "title": f"Build evidence item {index}",
                "description": "Implement and verify the linked evidence-backed capability.",
                "task_type": "implementation",
                "work_category": "functional",
                "acceptance_criteria": ["The evidenced behavior is implemented and verified."],
                "definition_of_done": ["Code review and automated tests are complete."],
                "confidence": 0.9,
            } for index, item in enumerate(context, start=1)],
        })


def test_prune_orphan_hierarchy_removes_unreferenced_feature():
    payload = json.loads(_ProviderResponse.one_item())
    payload["features"].append({
        **payload["features"][0],
        "feature_key": "F2",
        "title": "Unused generated feature",
    })

    batch = BacklogBatch.model_validate(_prune_orphan_hierarchy(json.dumps(payload)))

    assert [item.feature_key for item in batch.features] == ["F1"]


def test_fallback_backlog_batch_preserves_every_decomposition():
    context = [{
        "decomposition_id": f"DEC-{index:03d}", "requirement_ids": [f"REQ-{index:03d}"],
        "parent_capability": "Knowledge retrieval", "component_type": "feature",
        "title": f"Capability {index}", "description": "Deliver an evidence-backed product capability.",
        "suggested_backlog_level": "story", "rationale": "Supported by source evidence.",
    } for index in range(1, 5)]

    batch = _fallback_backlog_batch(context)

    assert len(batch.features) == len(batch.stories) == len(batch.tasks) == 4
    assert {item.decomposition_ids[0] for item in batch.stories} == {item["decomposition_id"] for item in context}


class _ProviderResponse:
    @staticmethod
    def one_item():
        return json.dumps({
            "epics": [{"epic_key": "E1", "decomposition_ids": ["DEC-001"], "title": "Evidence epic", "description": "Groups evidence-backed delivery work.", "architecture_layer": "Application", "business_value": "Delivers verified business capability.", "confidence": 0.9}],
            "features": [{"feature_key": "F1", "parent_epic_key": "E1", "decomposition_ids": ["DEC-001"], "title": "Evidence feature", "description": "Groups the supported story outcome.", "business_value": "Provides a traceable increment.", "confidence": 0.9}],
            "stories": [{"story_key": "S1", "parent_feature_key": "F1", "decomposition_ids": ["DEC-001"], "title": "Implement evidence", "user_story": "As a user, I want evidenced behavior so that value is delivered.", "description": "Implements the evidence-backed behavior.", "definition_of_done": ["Acceptance criteria pass."], "confidence": 0.9}],
            "tasks": [{"task_key": "T1", "parent_story_key": "S1", "decomposition_ids": ["DEC-001"], "title": "Build evidence", "description": "Implement and verify the evidence-backed behavior.", "task_type": "implementation", "work_category": "functional", "acceptance_criteria": ["Behavior is verified."], "definition_of_done": ["Tests pass."], "confidence": 0.9}],
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

    assert provider.calls == (100 + DECOMPOSITIONS_PER_BATCH - 1) // DECOMPOSITIONS_PER_BATCH
    assert len(generation.batch.epics) == provider.calls
    assert len(generation.batch.features) == 100
    assert len(generation.batch.stories) == 100
    assert len(generation.batch.tasks) == 100
    assert len({item.story_key for item in generation.batch.stories}) == 100
    assert len({item.task_key for item in generation.batch.tasks}) == 100
    referenced_ids = {
        decomposition_id
        for collection in (generation.batch.epics, generation.batch.features, generation.batch.stories, generation.batch.tasks)
        for item in collection
        for decomposition_id in item.decomposition_ids
    }
    assert referenced_ids == {item.stable_id for item in decompositions}
