import json
from types import SimpleNamespace

import pytest

from app.services.sprint_planning import STORIES_PER_BATCH, generate_sprint_plan


class _ScalarResult:
    def __init__(self, records):
        self._records = records

    def scalars(self):
        return self

    def all(self):
        return self._records


class _Database:
    def __init__(self, result_sets):
        self._result_sets = iter(result_sets)

    async def execute(self, _statement):
        return _ScalarResult(next(self._result_sets))

    async def scalar(self, _statement):
        return None


class _Provider:
    def __init__(self):
        self.calls = 0

    async def generate_text(self, prompt, _system_prompt):
        self.calls += 1
        payload = prompt.split("\n\nDATA:\n", maxsplit=1)[1]
        context, _ = json.JSONDecoder().raw_decode(payload)
        decisions = []
        for story in context["stories"]:
            story_number = int(story["stable_id"].split("-")[1])
            sprint_number = (story_number - 1) // 10 + 1
            decisions.append({
                "story_stable_id": story["stable_id"],
                "decision": "planned",
                "sprint_id": f"SPR-{sprint_number:03d}",
                "assignee_id": "MEM-001",
                "reason": "Fits verified sprint capacity and proposed ownership.",
                "confidence": 0.9,
            })
        return json.dumps({"decisions": decisions})


@pytest.mark.asyncio
async def test_generate_sprint_plan_covers_100_stories_across_10_sprints():
    stories = [SimpleNamespace(
        id=f"story-{index}", stable_id=f"STORY-{index:03d}", title=f"Story {index}",
        story_points=1, priority="Medium",
    ) for index in range(1, 101)]
    sprints = [SimpleNamespace(
        id=f"sprint-{index}", external_id=f"SPR-{index:03d}", name=f"Sprint {index}",
        start_date=f"2026-{index:02d}-01", end_date=f"2026-{index:02d}-14",
        capacity_points=10, committed_points=0,
    ) for index in range(1, 11)]
    members = [SimpleNamespace(id="member-1", external_id="MEM-001")]
    assignments = [SimpleNamespace(
        item_stable_id=story.stable_id, team_member_id="member-1",
    ) for story in stories]
    provider = _Provider()
    database = _Database([stories, sprints, assignments, members, [], []])

    generation = await generate_sprint_plan(database, "project-1", "session-1", provider)

    assert provider.calls == len(stories) // STORIES_PER_BATCH
    assert len(generation.batch.decisions) == 100
    assert {item.story_stable_id for item in generation.batch.decisions} == {
        item.stable_id for item in stories
    }
    sprint_counts = {}
    for decision in generation.batch.decisions:
        sprint_counts[decision.sprint_id] = sprint_counts.get(decision.sprint_id, 0) + 1
    assert sprint_counts == {f"SPR-{index:03d}": 10 for index in range(1, 11)}
