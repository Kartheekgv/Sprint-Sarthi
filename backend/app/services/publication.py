import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exporters.excel import build_workbook, validate_workbook
from app.models.entities import (
    AnalysisSession, AssignmentRecommendation, AuditEvent, BoardHealthResult, Clarification,
    ClarificationAnswer, ClarificationOption, Decomposition, Dependency, Document, DocumentSection,
    DuplicateCandidate, Epic, Feature, Holiday, Leave, Project, QualityResult, Requirement, Sprint,
    SprintPlanDecision, Task, TeamMember, UserStory, Department,
)


def _join(values: object) -> str:
    if isinstance(values, str):
        try:
            values = json.loads(values)
        except json.JSONDecodeError:
            return values
    return " | ".join(str(item) for item in values or [])


async def publish_session_workbook(
    db: AsyncSession, session: AnalysisSession, destination: Path
) -> str:
    project = await db.get(Project, session.project_id)
    documents = (await db.execute(select(Document).where(Document.project_id == session.project_id).order_by(Document.document_code))).scalars().all()
    document_by_id = {item.id: item for item in documents}
    sections = (await db.execute(select(DocumentSection).where(DocumentSection.document_id.in_(document_by_id)).order_by(DocumentSection.document_id, DocumentSection.chunk_index))).scalars().all() if document_by_id else []
    requirements = (await db.execute(select(Requirement).where(Requirement.session_id == session.id).order_by(Requirement.stable_id))).scalars().all()
    clarifications = (await db.execute(select(Clarification).where(Clarification.session_id == session.id).order_by(Clarification.created_at))).scalars().all()
    clarification_ids = {item.id for item in clarifications}
    answers = (await db.execute(select(ClarificationAnswer).where(ClarificationAnswer.clarification_id.in_(clarification_ids)))).scalars().all() if clarification_ids else []
    options = (await db.execute(select(ClarificationOption).where(ClarificationOption.clarification_id.in_(clarification_ids)))).scalars().all() if clarification_ids else []
    answer_by_question = {item.clarification_id: item for item in answers}
    option_by_id = {item.id: item for item in options}
    decompositions = (await db.execute(select(Decomposition).where(Decomposition.session_id == session.id).order_by(Decomposition.stable_id))).scalars().all()
    epics = (await db.execute(select(Epic).where(Epic.session_id == session.id).order_by(Epic.stable_id))).scalars().all()
    features = (await db.execute(select(Feature).where(Feature.session_id == session.id).order_by(Feature.stable_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session.id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session.id).order_by(Task.stable_id))).scalars().all()
    epic_by_id = {item.id: item for item in epics}
    feature_by_id = {item.id: item for item in features}
    story_by_id = {item.id: item for item in stories}
    title_by_stable_id = {item.stable_id: item.title for item in [*epics, *stories, *tasks]}
    dependencies = (await db.execute(select(Dependency).where(Dependency.session_id == session.id))).scalars().all()
    departments = (await db.execute(select(Department).where(Department.project_id == session.project_id))).scalars().all()
    department_by_id = {item.id: item for item in departments}
    members = (await db.execute(select(TeamMember).where(TeamMember.project_id == session.project_id).order_by(TeamMember.name))).scalars().all()
    member_by_id = {item.id: item for item in members}
    holidays = (await db.execute(select(Holiday).where(Holiday.project_id == session.project_id).order_by(Holiday.day))).scalars().all()
    leaves = (await db.execute(select(Leave).where(Leave.project_id == session.project_id).order_by(Leave.start_date))).scalars().all()
    sprints = (await db.execute(select(Sprint).where(Sprint.project_id == session.project_id).order_by(Sprint.start_date))).scalars().all()
    sprint_by_id = {item.id: item for item in sprints}
    sprint_order = {item.id: index for index, item in enumerate(sprints)}
    assignments = (await db.execute(select(AssignmentRecommendation).where(AssignmentRecommendation.session_id == session.id))).scalars().all()
    assignment_by_item = {item.item_stable_id: item for item in assignments}
    plans = (await db.execute(select(SprintPlanDecision).where(SprintPlanDecision.session_id == session.id))).scalars().all()
    plan_by_story_id = {item.story_id: item for item in plans}
    duplicates = (await db.execute(select(DuplicateCandidate).where(DuplicateCandidate.session_id == session.id))).scalars().all()
    quality = (await db.execute(select(QualityResult).where(QualityResult.session_id == session.id))).scalars().all()
    quality_by_item = {item.item_id: item for item in quality}
    health = await db.scalar(select(BoardHealthResult).where(BoardHealthResult.session_id == session.id))
    audits = (await db.execute(select(AuditEvent).where(AuditEvent.project_id == session.project_id).order_by(AuditEvent.created_at))).scalars().all()

    rows: dict[str, list[dict[str, object]]] = {
        "Summary": [
            {"Field": "Project", "Value": project.name if project else ""},
            {"Field": "Session", "Value": session.id},
            {"Field": "Status", "Value": session.status},
            {"Field": "Requirements", "Value": len(requirements)},
            {"Field": "Epics", "Value": len(epics)},
            {"Field": "Features", "Value": len(features)},
            {"Field": "Stories", "Value": len(stories)},
            {"Field": "Tasks", "Value": len(tasks)},
            {"Field": "Board Health", "Value": health.score if health else ""},
        ],
        "Source Documents": [{"Document ID": item.document_code, "Filename": item.original_name, "Media Type": item.media_type, "SHA-256": item.sha256, "Status": item.status} for item in documents],
        "Source Chunks": [{"Chunk ID": item.chunk_code, "Document ID": document_by_id[item.document_id].document_code, "Page": item.page or "", "Section": item.heading or item.section, "Content": item.content} for item in sections],
        "Requirements": [{"Requirement ID": item.stable_id, "Title": item.title, "Description": item.description, "Category": item.category, "Status": item.requirement_status, "Priority": item.priority, "Confidence": item.confidence, "Source Reference": _join(item.source_references_json)} for item in requirements],
        "Clarifications": [],
        "Decompositions": [{"Decomposition ID": item.stable_id, "Requirement IDs": _join(item.requirement_ids_json), "Capability": item.parent_capability, "Component Type": item.component_type, "Title": item.title, "Description": item.description, "Suggested Level": item.suggested_backlog_level, "Confidence": item.confidence} for item in decompositions],
        "Epics": [{"Epic ID": item.stable_id, "Architecture Layer": item.architecture_layer, "Epic Title": item.title, "Description": item.description, "Business Value": item.business_value, "Priority": item.priority, "Acceptance Criteria": _join(item.acceptance_criteria), "Source Reference": _join(item.source_references_json), "Quality Score": quality_by_item[item.stable_id].score if item.stable_id in quality_by_item else ""} for item in epics],
        "User Stories": [], "Tasks": [],
        "Dependencies": [{"Source ID": item.source_stable_id, "Source Title": title_by_stable_id.get(item.source_stable_id, ""), "Target ID": item.target_stable_id, "Target Title": title_by_stable_id.get(item.target_stable_id, ""), "Dependency Type": item.dependency_type, "Risk": item.risk, "Explanation": item.explanation} for item in dependencies],
        "Quality Report": [],
        "Team Members": [{"Member ID": item.external_id or item.id, "Name": item.name, "Role": item.role, "Skills": _join(item.skills_json), "Department": department_by_id[item.department_id].name if item.department_id in department_by_id else "", "Capacity Hours": item.capacity_hours or "", "Allocation Percent": item.allocation_percent, "Location": item.location} for item in members],
        "Holidays": [{"Date": str(item.day), "Name": item.name, "Location": item.location} for item in holidays],
        "Leaves": [{"Member ID": member_by_id[item.team_member_id].external_id or item.team_member_id, "Member Name": member_by_id[item.team_member_id].name, "Start Date": str(item.start_date), "End Date": str(item.end_date), "Reason": item.reason} for item in leaves],
        "Sprints": [{"Sprint ID": item.external_id or item.id, "Name": item.name, "Start Date": str(item.start_date), "End Date": str(item.end_date), "Capacity Points": item.capacity_points or "", "Committed Points": item.committed_points, "Committed": item.committed} for item in sprints],
        "Assignments": [], "Sprint Plan": [],
        "Duplicates": [{"Source ID": item.source_stable_id, "Target ID": item.target_stable_id, "Similarity": item.similarity, "Rationale": item.rationale, "Recommendation": item.recommendation, "Status": item.status} for item in duplicates],
        "Board Health": ([{"Metric": "Score", "Value": health.score}, {"Metric": "Risk Level", "Value": health.risk_level}] + [{"Metric": key, "Value": value} for key, value in json.loads(health.metrics_json).items()] + [{"Metric": "Issue", "Value": issue} for issue in json.loads(health.issues_json)]) if health else [],
        "Audit Trail": [{"Timestamp": item.created_at.isoformat(), "Actor": item.actor, "Action": item.action, "Entity Type": item.entity_type, "Entity ID": item.entity_id, "Details": item.details_json} for item in audits],
    }
    for item in clarifications:
        answer = answer_by_question.get(item.id)
        answer_text = ""
        if answer:
            answer_text = answer.custom_answer or (option_by_id[answer.option_id].label if answer.option_id in option_by_id else answer.action)
        rows["Clarifications"].append({"Requirement ID": item.requirement_stable_id, "Question": item.question, "Severity": item.severity, "Missing Field": item.missing_field, "Answer": answer_text, "Answer Origin": "human_provided" if answer else ""})
    ordered_stories = sorted(
        stories,
        key=lambda item: (
            sprint_order.get(plan_by_story_id[item.id].sprint_id, len(sprints))
            if item.id in plan_by_story_id and plan_by_story_id[item.id].sprint_id else len(sprints),
            item.stable_id,
        ),
    )
    planned_sprint_ids = set()
    for item in ordered_stories:
        feature = feature_by_id.get(item.feature_id)
        assignment = assignment_by_item.get(item.stable_id)
        plan = plan_by_story_id.get(item.id)
        if plan and plan.sprint_id:
            planned_sprint_ids.add(plan.sprint_id)
        rows["User Stories"].append({"Story ID": item.stable_id, "Feature ID": feature.stable_id if feature else "Legacy / unspecified", "Feature Title": feature.title if feature else "Legacy / unspecified", "Epic ID": epic_by_id[item.epic_id].stable_id, "Story Title": item.title, "User Story": item.user_story, "Description": item.description, "Acceptance Criteria": _join(item.acceptance_criteria), "Definition of Done": _join(item.definition_of_done_json), "Priority": item.priority, "Story Points": item.story_points or "", "Dependencies": _join([edge.target_stable_id for edge in dependencies if edge.source_stable_id == item.stable_id]), "Suggested Assignee": member_by_id[assignment.team_member_id].name if assignment else "", "Department": department_by_id[member_by_id[assignment.team_member_id].department_id].name if assignment and member_by_id[assignment.team_member_id].department_id in department_by_id else "", "Sprint": sprint_by_id[plan.sprint_id].name if plan and plan.sprint_id else "Deferred", "Status": item.status, "Quality Score": quality_by_item[item.stable_id].score if item.stable_id in quality_by_item else "", "Source Reference": _join(item.source_references_json)})
        rows["Sprint Plan"].append({"Sprint": sprint_by_id[plan.sprint_id].name if plan and plan.sprint_id else "Deferred", "Story ID": item.stable_id, "Story Title": item.title, "Story Points": item.story_points or "", "Suggested Assignee": member_by_id[plan.assignee_id].name if plan and plan.assignee_id else "", "Available Capacity": member_by_id[plan.assignee_id].capacity_hours if plan and plan.assignee_id else "", "Dependencies": _join([edge.target_stable_id for edge in dependencies if edge.source_stable_id == item.stable_id]), "Priority": item.priority, "Reason for Selection": plan.reason if plan else ""})
    for sprint in sprints:
        if sprint.id not in planned_sprint_ids:
            rows["Sprint Plan"].append({
                "Sprint": sprint.name,
                "Reason for Selection": "No stories planned for this sprint.",
            })
    for item in tasks:
        story = story_by_id[item.story_id]
        feature = feature_by_id.get(story.feature_id)
        assignment = assignment_by_item.get(item.stable_id)
        plan = plan_by_story_id.get(story.id)
        rows["Tasks"].append({"Task ID": item.stable_id, "Story ID": story.stable_id, "Feature ID": feature.stable_id if feature else "Legacy / unspecified", "Epic ID": epic_by_id[story.epic_id].stable_id, "Task Title": item.title, "Description": item.description, "Task Type": item.task_type, "Work Category": item.work_category, "Acceptance Criteria": _join(item.acceptance_criteria_json), "Definition of Done": _join(item.definition_of_done_json), "Priority": item.priority, "Estimated Hours": item.estimated_hours or "", "Dependencies": _join([edge.target_stable_id for edge in dependencies if edge.source_stable_id == item.stable_id]), "Suggested Assignee": member_by_id[assignment.team_member_id].name if assignment else "", "Department": department_by_id[member_by_id[assignment.team_member_id].department_id].name if assignment and member_by_id[assignment.team_member_id].department_id in department_by_id else "", "Sprint": sprint_by_id[plan.sprint_id].name if plan and plan.sprint_id else "Deferred", "Status": item.status, "Source Reference": _join(item.source_references_json)})
    rows["Assignments"] = [{"Item ID": item.item_stable_id, "Member ID": member_by_id[item.team_member_id].external_id or item.team_member_id, "Member Name": member_by_id[item.team_member_id].name, "Role": member_by_id[item.team_member_id].role, "Department": department_by_id[member_by_id[item.team_member_id].department_id].name if member_by_id[item.team_member_id].department_id in department_by_id else "", "Recommended Hours": item.recommended_hours or "", "Match Score": item.match_score, "Reason": item.reason, "Status": item.status} for item in assignments]
    quality_rows = []
    dependency_issue_ids = {
        stable_id
        for dependency in dependencies if dependency.risk in {"critical", "high"}
        for stable_id in (dependency.source_stable_id, dependency.target_stable_id)
    }
    duplicate_ids = {
        stable_id
        for candidate in duplicates
        for stable_id in (candidate.source_stable_id, candidate.target_stable_id)
    }
    for item in quality:
        issues = json.loads(item.details_json)["issues"]
        quality_rows.append({
            "Item ID": item.item_id,
            "Item Type": item.item_type,
            "Quality Score": item.score,
            "Missing Acceptance Criteria": "acceptance criteria present" in issues,
            "Duplicate": item.item_id in duplicate_ids,
            "Ambiguous": any(issue in issues for issue in ("title present", "description present", "user story present", "business value present")),
            "Dependency Issue": item.item_id in dependency_issue_ids,
            "Estimation Issue": "estimated" in issues,
            "Recommendation": "Review failed checks" if item.score < 80 else "Ready for review",
        })
    rows["Quality Report"] = quality_rows
    build_workbook(destination, rows)
    validate_workbook(destination)
    return hashlib.sha256(destination.read_bytes()).hexdigest()