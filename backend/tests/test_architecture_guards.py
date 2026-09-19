from datetime import date
from types import SimpleNamespace

import pytest

from app.schemas.backlog import BacklogBatch
from app.services.capacity import calculate_capacity_snapshot
from app.workflows.approval import ApprovalState, resume_approval_graph, start_approval_graph


def test_capacity_excludes_weekends_holidays_and_leave():
    member = SimpleNamespace(
        id="member-1", external_id="MEM-001", location="Pune",
        capacity_hours=40, allocation_percent=100,
    )
    sprint = SimpleNamespace(
        id="sprint-1", external_id="SPR-001",
        start_date=date(2026, 9, 14), end_date=date(2026, 9, 18),
    )
    holiday = SimpleNamespace(day=date(2026, 9, 16), location="Pune")
    leave = SimpleNamespace(
        team_member_id="member-1", start_date=date(2026, 9, 17), end_date=date(2026, 9, 17),
    )

    snapshot = calculate_capacity_snapshot(member, sprint, [holiday], [leave])

    assert snapshot.working_days == 3
    assert snapshot.holiday_days == 1
    assert snapshot.leave_days == 1
    assert snapshot.available_hours == 24


def test_backlog_contract_supports_more_than_one_hundred_tasks():
    assert BacklogBatch.model_fields["tasks"].metadata[-1].max_length == 1000


@pytest.mark.asyncio
async def test_approval_is_an_interruptible_langgraph_node(tmp_path):
    database_path = tmp_path / "checkpoints.sqlite"
    state: ApprovalState = {
        "project_id": "project-1",
        "session_id": "session-1",
        "thread_id": "thread-1",
        "status": "awaiting_approval",
        "decision": None,
    }

    await start_approval_graph(state, database_path)

    assert await resume_approval_graph("thread-1", "approve", database_path) == "approve"