import json
import re
from types import SimpleNamespace

import pytest

from app.services.decomposition import REQUIREMENTS_PER_BATCH, generate_decompositions
from app.services.requirements import generate_requirements


class _Rows:
    def __init__(self, records):
        self._records = records

    def all(self):
        return self._records

    def scalars(self):
        return self


class _SequenceDatabase:
    def __init__(self, results):
        self._results = iter(results)

    async def execute(self, _statement):
        return _Rows(next(self._results))


class _RequirementProvider:
    def __init__(self):
        self.seen_source_ids = []

    async def generate_text(self, prompt, _system_prompt):
        evidence = prompt.split("\n\nDOCUMENT EVIDENCE:\n", maxsplit=1)[1]
        source_ids = re.findall(r"^SOURCE_ID: (SRC-\d+)$", evidence, re.MULTILINE)
        self.seen_source_ids.extend(source_ids)
        return json.dumps({"requirements": [{
            "title": f"Requirement from {source_id}",
            "description": "Deliver the distinct behavior supported by this source evidence.",
            "category": "functional",
            "requirement_status": "explicit",
            "actors": ["User"],
            "systems": [],
            "business_rules": [],
            "constraints": [],
            "assumptions": [],
            "priority": "Unknown",
            "rationale": "The source explicitly describes required behavior.",
            "acceptance_criteria": [],
            "source_references": [source_id],
            "confidence": 0.9,
            "requires_clarification": False,
            "clarification_reasons": [],
        } for source_id in source_ids]})


class _DecompositionProvider:
    def __init__(self):
        self.calls = 0

    async def generate_text(self, prompt, _system_prompt):
        self.calls += 1
        context = json.loads(prompt.split("\n\nREQUIREMENTS:\n", maxsplit=1)[1])
        return json.dumps({"decompositions": [{
            "requirement_ids": [item["requirement_id"]],
            "parent_capability": "Evidence-backed capability",
            "component_type": "feature",
            "title": f"Deliver {item['requirement_id']}",
            "description": "Deliver the independently testable behavior in this requirement.",
            "suggested_backlog_level": "story",
            "rationale": "The requirement represents an independently valuable outcome.",
            "confidence": 0.9,
        } for item in context]})


@pytest.mark.asyncio
async def test_requirement_generation_processes_all_context_batches():
    document = SimpleNamespace(
        id="document-1", document_code="DOC-001", original_name="sample.docx", status="processed"
    )
    sections = [(SimpleNamespace(
        heading=f"Section {index}", page=index, chunk_code=f"CHUNK-{index:03d}",
        content="Evidence " + ("x" * 650), created_at=index, chunk_index=index,
    ), document) for index in range(1, 4)]
    provider = _RequirementProvider()

    generation = await generate_requirements(
        _SequenceDatabase([sections, []]), "project-1", "session-1", provider,
        SimpleNamespace(max_llm_context_chars=1000),
    )

    assert provider.seen_source_ids == ["SRC-0001", "SRC-0002", "SRC-0003"]
    assert len(generation.batch.requirements) == 3


@pytest.mark.asyncio
async def test_decomposition_generation_batches_all_requirements():
    requirements = [SimpleNamespace(
        stable_id=f"REQ-{index:03d}", title=f"Requirement {index}",
        description="A distinct evidence-backed requirement.", category="functional",
        actors_json="[]", systems_json="[]", business_rules_json="[]",
        constraints_json="[]", assumptions_json="[]", source_references_json="[]",
    ) for index in range(1, 26)]
    provider = _DecompositionProvider()

    generation = await generate_decompositions(
        _SequenceDatabase([requirements]), "session-1", provider,
    )

    assert provider.calls == 25 // REQUIREMENTS_PER_BATCH + 1
    assert len(generation.batch.decompositions) == 25
    assert {item.requirement_ids[0] for item in generation.batch.decompositions} == {
        item.stable_id for item in requirements
    }