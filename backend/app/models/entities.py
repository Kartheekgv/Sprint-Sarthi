from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Record(Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Project(Record):
    __tablename__ = "projects"
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)


class Document(Record):
    __tablename__ = "documents"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    document_code: Mapped[str] = mapped_column(String(50))
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default="uploaded", index=True)
    language: Mapped[str] = mapped_column(String(20), default="unknown")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_documents_nonempty"),
        UniqueConstraint("project_id", "document_code", name="uq_project_document_code"),
    )


class DocumentSection(Record):
    __tablename__ = "document_sections"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_code: Mapped[str] = mapped_column(String(50))
    section: Mapped[str] = mapped_column(String(255), default="")
    heading: Mapped[str] = mapped_column(String(500), default="")
    page: Mapped[int | None] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),
        UniqueConstraint("document_id", "chunk_code", name="uq_document_chunk_code"),
    )


class AnalysisSession(Record):
    __tablename__ = "analysis_sessions"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    thread_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="created", index=True)
    current_node: Mapped[str | None] = mapped_column(String(80))


class ChatMessage(Record):
    __tablename__ = "chat_messages"
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)


class Clarification(Record):
    __tablename__ = "clarifications"
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True)
    requirement_stable_id: Mapped[str] = mapped_column(String(50), index=True)
    question: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    missing_field: Mapped[str] = mapped_column(String(100))
    recommended_answer_type: Mapped[str] = mapped_column(String(30))
    blocking: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    recommended_option_id: Mapped[str | None] = mapped_column(String(36))
    allow_custom_answer: Mapped[bool] = mapped_column(Boolean, default=True)
    source_references_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)


class ClarificationOption(Record):
    __tablename__ = "clarification_options"
    clarification_id: Mapped[str] = mapped_column(ForeignKey("clarifications.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("clarification_id", "position", name="uq_clarification_option_position"),)


class ClarificationAnswer(Record):
    __tablename__ = "clarification_answers"
    clarification_id: Mapped[str] = mapped_column(ForeignKey("clarifications.id", ondelete="CASCADE"), unique=True)
    option_id: Mapped[str | None] = mapped_column(ForeignKey("clarification_options.id"))
    custom_answer: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(20))
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")


class Requirement(Record):
    __tablename__ = "requirements"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True)
    stable_id: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), index=True)
    requirement_status: Mapped[str] = mapped_column(String(20), default="candidate", index=True)
    actors_json: Mapped[str] = mapped_column(Text, default="[]")
    systems_json: Mapped[str] = mapped_column(Text, default="[]")
    business_rules_json: Mapped[str] = mapped_column(Text, default="[]")
    constraints_json: Mapped[str] = mapped_column(Text, default="[]")
    assumptions_json: Mapped[str] = mapped_column(Text, default="[]")
    priority: Mapped[str] = mapped_column(String(20), index=True)
    rationale: Mapped[str] = mapped_column(Text)
    acceptance_criteria_json: Mapped[str] = mapped_column(Text, default="[]")
    source_references_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    requires_clarification: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    clarification_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    __table_args__ = (UniqueConstraint("project_id", "stable_id", name="uq_project_requirement_stable_id"),)


class Decomposition(Record):
    __tablename__ = "decompositions"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True)
    stable_id: Mapped[str] = mapped_column(String(50))
    requirement_ids_json: Mapped[str] = mapped_column(Text)
    parent_capability: Mapped[str] = mapped_column(String(300))
    component_type: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    suggested_backlog_level: Mapped[str] = mapped_column(String(20), index=True)
    rationale: Mapped[str] = mapped_column(Text)
    source_references_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float)
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    __table_args__ = (UniqueConstraint("project_id", "stable_id", name="uq_project_decomposition_stable_id"),)


class Epic(Record):
    __tablename__ = "epics"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    stable_id: Mapped[str] = mapped_column(String(50), unique=True)
    decomposition_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    requirement_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    business_value: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20))
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")
    source_references_json: Mapped[str] = mapped_column(Text, default="[]")
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="draft")


class UserStory(Record):
    __tablename__ = "user_stories"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    epic_id: Mapped[str] = mapped_column(ForeignKey("epics.id", ondelete="CASCADE"), index=True)
    stable_id: Mapped[str] = mapped_column(String(50), unique=True)
    decomposition_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    requirement_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    title: Mapped[str] = mapped_column(String(500))
    user_story: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    acceptance_criteria: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20))
    story_points: Mapped[int | None] = mapped_column(Integer)
    estimation_rationale: Mapped[str] = mapped_column(Text, default="")
    source_references_json: Mapped[str] = mapped_column(Text, default="[]")
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="draft")


class Task(Record):
    __tablename__ = "tasks"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("user_stories.id", ondelete="CASCADE"), index=True)
    stable_id: Mapped[str] = mapped_column(String(50), unique=True)
    decomposition_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    requirement_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(30))
    priority: Mapped[str] = mapped_column(String(20))
    estimated_hours: Mapped[float | None] = mapped_column(Float)
    estimation_rationale: Mapped[str] = mapped_column(Text, default="")
    source_references_json: Mapped[str] = mapped_column(Text, default="[]")
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="draft")


class Dependency(Record):
    __tablename__ = "dependencies"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_stable_id: Mapped[str] = mapped_column(String(50), index=True)
    target_stable_id: Mapped[str] = mapped_column(String(50), index=True)
    dependency_type: Mapped[str] = mapped_column(String(30))
    risk: Mapped[str] = mapped_column(String(20), default="medium")
    explanation: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (
        CheckConstraint("source_stable_id <> target_stable_id", name="ck_dependency_not_self"),
        UniqueConstraint("project_id", "source_stable_id", "target_stable_id", name="uq_dependency_edge"),
    )


class Department(Record):
    __tablename__ = "departments"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(150))
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_department"),)


class TeamMember(Record):
    __tablename__ = "team_members"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    external_id: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(150), default="")
    skills_json: Mapped[str] = mapped_column(Text, default="[]")
    capacity_hours: Mapped[float | None] = mapped_column(Float)
    allocation_percent: Mapped[float] = mapped_column(Float, default=100.0)
    location: Mapped[str] = mapped_column(String(150), default="")
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")


class Holiday(Record):
    __tablename__ = "holidays"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(String(150))
    location: Mapped[str] = mapped_column(String(150), default="")
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (UniqueConstraint("project_id", "day", name="uq_project_holiday"),)


class Leave(Record):
    __tablename__ = "leaves"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    team_member_id: Mapped[str] = mapped_column(ForeignKey("team_members.id", ondelete="CASCADE"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(300), default="")
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_leave_dates"),)


class Sprint(Record):
    __tablename__ = "sprints"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(150))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    capacity_points: Mapped[float | None] = mapped_column(Float)
    committed_points: Mapped[float] = mapped_column(Float, default=0.0)
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    committed: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_sprint_dates"),)


class Capacity(Record):
    __tablename__ = "capacity"
    sprint_id: Mapped[str] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"), index=True)
    team_member_id: Mapped[str] = mapped_column(ForeignKey("team_members.id", ondelete="CASCADE"), index=True)
    available_hours: Mapped[float] = mapped_column(Float)
    __table_args__ = (UniqueConstraint("sprint_id", "team_member_id", name="uq_sprint_member_capacity"),)


class SprintItem(Record):
    __tablename__ = "sprint_items"
    sprint_id: Mapped[str] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"), index=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("user_stories.id", ondelete="CASCADE"), index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("team_members.id"))
    reason: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("sprint_id", "story_id", name="uq_sprint_story"),)


class SprintPlanDecision(Record):
    __tablename__ = "sprint_plan_decisions"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    story_id: Mapped[str] = mapped_column(ForeignKey("user_stories.id", ondelete="CASCADE"), index=True)
    sprint_id: Mapped[str | None] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"), index=True)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("team_members.id"), index=True)
    decision: Mapped[str] = mapped_column(String(20), index=True)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True)
    __table_args__ = (
        UniqueConstraint("session_id", "story_id", name="uq_session_sprint_plan_story"),
        CheckConstraint("decision IN ('planned', 'deferred')", name="ck_sprint_plan_decision"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_sprint_plan_confidence"),
    )


class AssignmentRecommendation(Record):
    __tablename__ = "assignment_recommendations"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    item_stable_id: Mapped[str] = mapped_column(String(50), index=True)
    team_member_id: Mapped[str] = mapped_column(ForeignKey("team_members.id", ondelete="CASCADE"), index=True)
    recommended_hours: Mapped[float | None] = mapped_column(Float)
    match_score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True)
    __table_args__ = (
        UniqueConstraint("session_id", "item_stable_id", name="uq_session_assignment_item"),
        CheckConstraint("match_score BETWEEN 0 AND 1", name="ck_assignment_match_score"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_assignment_confidence"),
    )


class Job(Record):
    __tablename__ = "jobs"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint("progress BETWEEN 0 AND 100", name="ck_job_progress"),)


class AgentExecution(Record):
    __tablename__ = "agent_executions"
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True)
    node_name: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(20))
    model: Mapped[str | None] = mapped_column(String(150))
    prompt_hash: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    remaining_tokens: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)


class QualityResult(Record):
    __tablename__ = "quality_results"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    item_id: Mapped[str] = mapped_column(String(50), index=True)
    item_type: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 100", name="ck_quality_score"),)


class BoardHealthResult(Record):
    __tablename__ = "board_health_results"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(20), index=True)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    issues_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="review_required", index=True)
    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 100", name="ck_board_health_score"),)


class DuplicateCandidate(Record):
    __tablename__ = "duplicate_candidates"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    source_stable_id: Mapped[str] = mapped_column(String(50), index=True)
    target_stable_id: Mapped[str] = mapped_column(String(50), index=True)
    similarity: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column(Float)
    provenance_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="candidate", index=True)
    __table_args__ = (
        CheckConstraint("source_stable_id <> target_stable_id", name="ck_duplicate_not_self"),
        CheckConstraint("similarity BETWEEN 0 AND 1", name="ck_duplicate_similarity"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_duplicate_confidence"),
        UniqueConstraint("session_id", "source_stable_id", "target_stable_id", name="uq_session_duplicate_pair"),
    )


class Approval(Record):
    __tablename__ = "approvals"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(50))
    approved_by: Mapped[str] = mapped_column(String(200))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    decision: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")


class Export(Record):
    __tablename__ = "exports"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))


class AuditEvent(Record):
    __tablename__ = "audit_events"
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    actor: Mapped[str] = mapped_column(String(200), default="system")
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    details_json: Mapped[str] = mapped_column(Text, default="{}")


Index("ix_dependencies_project_source", Dependency.project_id, Dependency.source_stable_id)
