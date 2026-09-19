from datetime import date, timedelta
from collections.abc import Iterable

from app.models.entities import Holiday, Leave, Sprint, TeamMember
from app.schemas.capacity import CapacitySnapshot


def _period_days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _matches_location(location: str, holiday_location: str) -> bool:
    return not holiday_location or not location or location.casefold() == holiday_location.casefold()


def calculate_capacity_snapshot(
    member: TeamMember,
    sprint: Sprint,
    holidays: Iterable[Holiday],
    leaves: Iterable[Leave],
) -> CapacitySnapshot:
    days = _period_days(sprint.start_date, sprint.end_date)
    member_holidays = {
        item.day for item in holidays if _matches_location(member.location, item.location)
    }
    member_leaves = {
        day
        for item in leaves
        if item.team_member_id == member.id
        for day in _period_days(max(item.start_date, sprint.start_date), min(item.end_date, sprint.end_date))
    }
    weekdays = {day for day in days if day.weekday() < 5}
    holiday_days = weekdays & member_holidays
    leave_days = weekdays & member_leaves
    working_days = weekdays - holiday_days - leave_days
    base_hours = max(float(member.capacity_hours or 0), 0.0)
    allocation = max(min(float(member.allocation_percent or 0), 100.0), 0.0)
    period_weekdays = max(len(weekdays), 1)
    available_hours = base_hours * allocation / 100 * len(working_days) / period_weekdays
    return CapacitySnapshot(
        member_id=member.external_id or member.id,
        sprint_id=sprint.external_id or sprint.id,
        period_start=sprint.start_date,
        period_end=sprint.end_date,
        working_days=len(working_days),
        leave_days=len(leave_days),
        holiday_days=len(holiday_days),
        allocation_percent=allocation,
        available_hours=round(available_hours, 2),
    )


def capacity_by_member(
    members: Iterable[TeamMember],
    sprints: Iterable[Sprint],
    holidays: Iterable[Holiday],
    leaves: Iterable[Leave],
) -> tuple[dict[str, float], list[CapacitySnapshot]]:
    snapshots = [
        calculate_capacity_snapshot(member, sprint, holidays, leaves)
        for member in members
        for sprint in sprints
    ]
    totals: dict[str, float] = {}
    for snapshot in snapshots:
        totals[snapshot.member_id] = round(totals.get(snapshot.member_id, 0.0) + snapshot.available_hours, 2)
    return totals, snapshots