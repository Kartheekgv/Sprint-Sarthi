import asyncio
import json
from pathlib import Path
from time import monotonic
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Path as ApiPath, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models.entities import (
    AgentExecution, AnalysisSession, Approval, AssignmentRecommendation, AuditEvent, BoardHealthResult, Clarification, ClarificationAnswer,
    ChatMessage, ClarificationOption, Decomposition, Dependency, Document, DocumentSection, DuplicateCandidate, Epic, Job, Project, Requirement,
    EstimationBrief, Export, Feature, NewStoryCheck, QualityClarification, QualityResult, Sprint, SprintItem, SprintPlanDecision, SprintScopeReview, Task, UserStory,
)
from app.providers import get_llm_provider
from app.providers.base import LLMProvider
from app.providers.llmaas import LLMAASError
from app.schemas.clarifications import (
    AnalysisSessionRead, ClarificationAnswerCreate, ClarificationAnswerResult,
    AgentFeedbackDraft, AgentMessageRead, AgentPromptCreate, AgentPromptResult, ClarificationHistoryRead,
    ClarificationOptionRead, ClarificationRead,
)
from app.schemas.backlog import BacklogGenerationResult, EpicRead, FeatureRead, StoryRead, TaskRead
from app.schemas.evidence import BacklogItemType, BacklogSourcesRead
from app.schemas.decomposition import DecompositionGenerationResult, DecompositionRead
from app.schemas.dependencies import DependencyGenerationResult, DependencyRead
from app.schemas.duplicates import (
    DuplicateGenerationResult, DuplicateRead, NewStoryAssessment, NewStoryCheckCreate,
    NewStoryCheckRead, NewStoryConfirmCreate, NewStoryCreateResult,
)
from app.schemas.projects import DocumentChunkRead, DocumentRead, JobRead, ProjectCreate, ProjectRead
from app.schemas.planning_data import AssignmentGenerationResult, AssignmentRead, PlanningImportResult
from app.schemas.sprint_planning import SprintDecisionRead, SprintPlanningResult, SprintScopeReviewCreate, SprintScopeReviewRead
from app.schemas.quality import (
    BoardHealthGenerationResult, BoardHealthRead, QualityClarificationAnswerCreate,
    QualityClarificationRead, QualityGenerationResult, QualityRead,
)
from app.schemas.approval import ApprovalDecisionCreate, ApprovalDecisionRead, ExportRead, WorkbookPreviewRead
from app.schemas.estimation import EstimationBriefCreate, EstimationBriefRead, EstimationBriefWorkspace
from app.schemas.requirements import RequirementGenerationResult, RequirementRead
from app.schemas.provenance import ProvenanceValue
from app.schemas.usage import AgentUsageRead, OperationalLogsRead, SessionUsageRead
from app.services.document_extraction import DocumentExtractionError, extract_document
from app.services.backlog import backlog_to_dicts, generate_backlog, persist_backlog
from app.services.enrichment import generate_enrichment, persist_enrichment
from app.services.estimation import generate_estimates, persist_estimates
from app.services.dependencies import dependency_to_dict, generate_dependencies, persist_dependencies
from app.services.duplicates import duplicate_to_dict, generate_duplicates, persist_duplicates
from app.services.new_stories import assess_new_story
from app.services.decomposition import decomposition_to_dict, generate_decompositions, persist_decompositions
from app.services.evidence import resolve_item_evidence
from app.services.clarifications import generate_clarifications, persist_clarifications
from app.services.uploads import save_upload
from app.services.requirements import generate_requirements, persist_requirements, requirement_to_dict
from app.services.planning_data import build_planning_template, parse_planning_workbook, persist_planning_workbook
from app.services.assignment import assignments_to_dicts, generate_assignments, persist_assignments
from app.services.sprint_planning import ORDERING_HEURISTIC, generate_sprint_plan, persist_sprint_plan, sprint_plan_forecast, sprint_plan_to_dicts
from app.services.quality import (
    QUALITY_THRESHOLD, apply_quality_clarification, board_health_to_dict,
    create_quality_clarifications, quality_clarification_to_dict, quality_to_dict,
    run_board_health, run_quality_checks,
)
from app.services.publication import publish_session_workbook
from app.exporters.excel import preview_workbook
from app.workflows.clarification import ClarificationState, resume_clarification_graph, start_clarification_graph
from app.workflows.backlog import BacklogState, checkpoint_backlog_stage
from app.workflows.enrichment import EnrichmentState, checkpoint_enrichment_stage
from app.workflows.estimation import EstimationState, checkpoint_estimation_stage
from app.workflows.dependencies import DependencyState, checkpoint_dependency_stage
from app.workflows.duplicates import DuplicateState, checkpoint_duplicate_stage
from app.workflows.assignment import AssignmentState, checkpoint_assignment_stage
from app.workflows.sprint_planning import SprintPlanningState, checkpoint_sprint_planning_stage
from app.workflows.quality import ValidationState, checkpoint_validation_stage
from app.workflows.decomposition import DecompositionState, checkpoint_decomposition_stage
from app.workflows.requirements import RequirementState, checkpoint_requirement_stage


router = APIRouter()


def estimation_brief_to_read(record: EstimationBrief) -> EstimationBriefRead:
    return EstimationBriefRead(
        id=record.id,
        session_id=record.session_id,
        answered_by=record.answered_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
        **json.loads(record.answers_json),
    )


def new_story_check_to_read(record: NewStoryCheck) -> NewStoryCheckRead:
    return NewStoryCheckRead(
        id=record.id,
        session_id=record.session_id,
        proposal=NewStoryCheckCreate.model_validate(json.loads(record.input_json)),
        status=record.status,
        **json.loads(record.result_json),
    )



def project_workflow_state(project: Project, documents: list[Document], session: AnalysisSession | None) -> dict[str, object]:
    if session is None:
        if not documents:
            return {"workflow_state": "Project intake", "current_node": "Intake", "agent_index": 0}
        if any(item.status != "processed" for item in documents):
            return {"workflow_state": "Document analysis", "current_node": "Document Analysis", "agent_index": 1}
        return {"workflow_state": "Ready for clarification", "current_node": "Clarification", "agent_index": 2}

    agent_by_node = {
        "Clarification": 2, "Requirement": 3, "Decomposition": 4, "Backlog": 5,
        "Enrichment": 6, "Estimation": 7, "Dependency": 8, "Sprint": 11,
        "Duplicate": 12, "Quality": 13, "BoardHealth": 14, "HumanApproval": 15,
        "Publisher": 16, "Complete": 16,
    }
    state_by_status = {
        "processing_requirements": "Analyzing requirements",
        "processing_clarifications": "Preparing clarifications",
        "awaiting_clarification": "Awaiting clarification",
        "clarifications_complete": "Ready for requirements",
        "requirements_complete": "Ready for decomposition",
        "decomposition_complete": "Ready for backlog",
        "backlog_complete": "Ready for enrichment",
        "enrichment_complete": "Ready for estimation",
        "estimation_complete": "Ready for dependency analysis",
        "dependencies_complete": "Awaiting planning data",
        "planning_data_ready": "Ready for assignment",
        "assignment_complete": "Ready for sprint planning",
        "sprint_planning_complete": "Ready for duplicate detection",
        "duplicates_complete": "Ready for quality review",
        "quality_clarification_required": "Quality clarification required",
        "quality_complete": "Ready for board health",
        "awaiting_approval": "Awaiting human approval",
        "approved": "Approved, ready to publish",
        "review_rejected": "Review rejected",
        "changes_requested": "Changes requested",
        "published": "Published",
        "failed": "Needs attention",
    }
    agent_index = 9 if session.status == "dependencies_complete" else 10 if session.status == "planning_data_ready" else agent_by_node.get(session.current_node or "", 2)
    return {
        "workflow_state": state_by_status.get(session.status, session.status.replace("_", " ").title()),
        "current_node": session.current_node,
        "agent_index": agent_index,
    }

@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(db: AsyncSession = Depends(get_session)) -> list[dict[str, object]]:
    projects = (await db.execute(
        select(Project).order_by(Project.updated_at.desc(), Project.created_at.desc())
    )).scalars().all()
    result = []
    for project in projects:
        documents = (await db.execute(select(Document).where(Document.project_id == project.id))).scalars().all()
        session = (await db.execute(
            select(AnalysisSession).where(AnalysisSession.project_id == project.id).order_by(AnalysisSession.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        result.append({
            "id": project.id, "name": project.name, "description": project.description,
            "status": project.status, "created_at": project.created_at,
            **project_workflow_state(project, list(documents), session),
        })
    return result


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_session)) -> Project:
    project = Project(name=payload.name.strip(), description=payload.description.strip())
    db.add(project)
    await db.flush()
    db.add(AuditEvent(project_id=project.id, action="project.created", entity_type="project", entity_id=project.id))
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    documents = (await db.execute(select(Document).where(Document.project_id == project_id))).scalars().all()
    exports = (await db.execute(select(Export).where(Export.project_id == project_id))).scalars().all()
    upload_paths = [(settings.upload_dir / item.stored_name).resolve() for item in documents]
    export_paths = [Path(item.filename).resolve() for item in exports]
    await db.delete(project)
    await db.commit()
    upload_root = settings.upload_dir.resolve()
    export_root = settings.export_dir.resolve()
    for path in upload_paths:
        if upload_root in path.parents:
            path.unlink(missing_ok=True)
    for path in export_paths:
        if export_root in path.parents:
            path.unlink(missing_ok=True)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentRead])
async def list_project_documents(
    project_id: str,
    db: AsyncSession = Depends(get_session),
) -> list[Document]:
    if await db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return (await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )).scalars().all()


@router.get("/projects/{project_id}/resume")
async def resume_project_workflow(
    project_id: str,
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    documents = list((await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at)
    )).scalars().all())
    session = (await db.execute(
        select(AnalysisSession).where(AnalysisSession.project_id == project_id).order_by(AnalysisSession.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    state = project_workflow_state(project, documents, session)
    base: dict[str, object] = {
        "project": ProjectRead.model_validate(project).model_dump(),
        "documents": [DocumentRead.model_validate(item).model_dump() for item in documents],
        "session": AnalysisSessionRead.model_validate(session).model_dump() if session else None,
        **state,
        "clarification": None, "clarifications_complete": False,
        "requirements": [], "decompositions": [], "backlog": None,
        "enriched": False, "estimated": False, "dependencies": None,
        "planning_ready": False, "assignments": [], "sprint_plan": [],
        "duplicate_candidates": [], "duplicates_complete": False,
        "quality_results": [], "board_health": None,
        "approved": False, "published_export": None,
    }
    if session is None:
        return base

    status_order = [
        "awaiting_clarification", "clarifications_complete", "requirements_complete",
        "decomposition_complete", "backlog_complete", "enrichment_complete",
        "estimation_complete", "dependencies_complete", "planning_data_ready",
        "assignment_complete", "sprint_planning_complete", "duplicates_complete",
        "quality_clarification_required", "quality_complete", "awaiting_approval", "approved", "published",
    ]
    progress_status = {
        "review_rejected": "awaiting_approval",
        "changes_requested": "awaiting_approval",
    }.get(session.status, session.status)
    rank = status_order.index(progress_status) if progress_status in status_order else -1
    base["clarifications_complete"] = rank >= status_order.index("clarifications_complete")
    if session.status == "awaiting_clarification":
        pending = (await db.execute(
            select(Clarification).where(Clarification.session_id == session.id, Clarification.status == "pending")
            .order_by(Clarification.created_at, Clarification.id).limit(1)
        )).scalar_one_or_none()
        if pending:
            options = (await db.execute(
                select(ClarificationOption).where(ClarificationOption.clarification_id == pending.id).order_by(ClarificationOption.position)
            )).scalars().all()
            base["clarification"] = {
                "id": pending.id, "session_id": session.id, "requirement_id": pending.requirement_stable_id,
                "question": pending.question, "reason": pending.reason, "severity": pending.severity,
                "missing_field": pending.missing_field, "recommended_answer_type": pending.recommended_answer_type,
                "blocking": pending.blocking, "required": pending.required,
                "recommended_option_id": pending.recommended_option_id or "",
                "allow_custom_answer": pending.allow_custom_answer,
                "source_references": json.loads(pending.source_references_json),
                "options": [{"id": item.id, "label": item.label, "position": item.position} for item in options],
            }
    if rank >= status_order.index("requirements_complete"):
        requirements = (await db.execute(select(Requirement).where(Requirement.session_id == session.id).order_by(Requirement.stable_id))).scalars().all()
        base["requirements"] = [RequirementRead.model_validate(requirement_to_dict(item)).model_dump() for item in requirements]
    if rank >= status_order.index("decomposition_complete"):
        decompositions = (await db.execute(select(Decomposition).where(Decomposition.session_id == session.id).order_by(Decomposition.stable_id))).scalars().all()
        base["decompositions"] = [DecompositionRead.model_validate(decomposition_to_dict(item)).model_dump() for item in decompositions]
    if rank >= status_order.index("backlog_complete"):
        epics = (await db.execute(select(Epic).where(Epic.session_id == session.id).order_by(Epic.stable_id))).scalars().all()
        features = (await db.execute(select(Feature).where(Feature.session_id == session.id).order_by(Feature.stable_id))).scalars().all()
        stories = (await db.execute(select(UserStory).where(UserStory.session_id == session.id).order_by(UserStory.stable_id))).scalars().all()
        tasks = (await db.execute(select(Task).where(Task.session_id == session.id).order_by(Task.stable_id))).scalars().all()
        epic_rows, feature_rows, story_rows, task_rows = backlog_to_dicts(epics, features, stories, tasks)
        base["backlog"] = {"epics": epic_rows, "features": feature_rows, "stories": story_rows, "tasks": task_rows}
        base["enriched"] = rank >= status_order.index("enrichment_complete")
        base["estimated"] = rank >= status_order.index("estimation_complete")
    if rank >= status_order.index("dependencies_complete"):
        dependencies = (await db.execute(select(Dependency).where(Dependency.session_id == session.id).order_by(Dependency.created_at))).scalars().all()
        base["dependencies"] = [dependency_to_dict(item) for item in dependencies]
    base["planning_ready"] = rank >= status_order.index("planning_data_ready")
    if rank >= status_order.index("assignment_complete"):
        assignments = (await db.execute(select(AssignmentRecommendation).where(AssignmentRecommendation.session_id == session.id).order_by(AssignmentRecommendation.item_stable_id))).scalars().all()
        base["assignments"] = await assignments_to_dicts(db, assignments)
    if rank >= status_order.index("sprint_planning_complete"):
        decisions = (await db.execute(select(SprintPlanDecision).where(SprintPlanDecision.session_id == session.id).order_by(SprintPlanDecision.created_at))).scalars().all()
        base["sprint_plan"] = await sprint_plan_to_dicts(db, decisions)
    if rank >= status_order.index("duplicates_complete"):
        duplicates = (await db.execute(select(DuplicateCandidate).where(DuplicateCandidate.session_id == session.id))).scalars().all()
        base["duplicate_candidates"] = [duplicate_to_dict(item) for item in duplicates]
        base["duplicates_complete"] = True
    if rank >= status_order.index("quality_complete"):
        quality = (await db.execute(select(QualityResult).where(QualityResult.session_id == session.id))).scalars().all()
        base["quality_results"] = [quality_to_dict(item) for item in quality]
    if rank >= status_order.index("awaiting_approval"):
        health = await db.scalar(select(BoardHealthResult).where(BoardHealthResult.session_id == session.id))
        base["board_health"] = board_health_to_dict(health) if health else None
    base["approved"] = rank >= status_order.index("approved")
    if session.status == "published":
        export = await db.scalar(select(Export).where(Export.session_id == session.id, Export.status == "completed"))
        if export:
            base["published_export"] = {"filename": "sprint_sarthi_backlog.xlsx", "sha256": export.sha256, "download_url": f"/api/v1/exports/{export.id}/download"}
    return base


@router.post("/projects/{project_id}/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Document:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    project_dir = settings.upload_dir / project_id
    stored_name, size, digest = await save_upload(file, project_dir, settings.max_upload_mb * 1024 * 1024)
    document_count = await db.scalar(select(func.count(Document.id)).where(Document.project_id == project_id))
    document = Document(
        project_id=project_id,
        document_code=f"DOC-{(document_count or 0) + 1:03d}",
        original_name=Path(file.filename or "document").name,
        stored_name=f"{project_id}/{stored_name}",
        media_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        sha256=digest,
    )
    db.add(document)
    await db.flush()
    db.add(AuditEvent(project_id=project_id, action="document.uploaded", entity_type="document", entity_id=document.id))
    await db.commit()
    await db.refresh(document)
    return document


@router.post("/documents/{document_id}/process", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def process_document(
    document_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Job:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    source_path = (settings.upload_dir / document.stored_name).resolve()
    if settings.upload_dir.resolve() not in source_path.parents or not source_path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored document not found")

    job = Job(project_id=document.project_id, kind="document_processing", status="running", progress=10)
    document.status = "processing"
    db.add(job)
    await db.commit()
    try:
        extracted = await asyncio.to_thread(extract_document, source_path)
        await db.execute(delete(DocumentSection).where(DocumentSection.document_id == document.id))
        for chunk_index, section in enumerate(extracted):
            db.add(DocumentSection(
                document_id=document.id,
                chunk_code=f"CHUNK-{chunk_index + 1:03d}",
                section=section.section,
                heading=section.heading,
                page=section.page,
                chunk_index=chunk_index,
                content=section.content,
                token_count=len(section.content.split()),
                extraction_confidence=1.0,
            ))
            document.extraction_confidence = 1.0
        document.status = "processed"
        job.status = "completed"
        job.progress = 100
        db.add(AuditEvent(
            project_id=document.project_id,
            action="document.processed",
            entity_type="document",
            entity_id=document.id,
            details_json=f'{{"sections":{len(extracted)}}}',
        ))
        await db.commit()
        await db.refresh(job)
        return job
    except DocumentExtractionError as error:
        document.status = "failed"
        job.status = "failed"
        job.error = str(error)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkRead])
async def get_document_chunks(document_id: str, db: AsyncSession = Depends(get_session)) -> list[DocumentChunkRead]:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    chunks = (await db.execute(
        select(DocumentSection)
        .where(DocumentSection.document_id == document_id)
        .order_by(DocumentSection.chunk_index)
    )).scalars().all()
    return [DocumentChunkRead(
        id=chunk.id,
        chunk_id=chunk.chunk_code,
        document_id=document.document_code,
        file_name=document.original_name,
        page_number=chunk.page,
        section_heading=chunk.heading,
        content=chunk.content,
        token_count=chunk.token_count,
        metadata=json.loads(chunk.metadata_json),
        extraction_confidence=chunk.extraction_confidence,
        embedding_status="generated" if json.loads(chunk.metadata_json).get("embedding_dimensions") else "not_generated",
        embedding_model=json.loads(chunk.metadata_json).get("embedding_model"),
        embedding_dimensions=json.loads(chunk.metadata_json).get("embedding_dimensions"),
    ) for chunk in chunks]


async def prepare_analysis_session(
    project_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> None:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        return
    requirement_execution = AgentExecution(
        session_id=session.id,
        node_name="Requirement",
        status="running",
        model=settings.llm_model,
    )
    db.add(requirement_execution)
    await db.commit()
    requirement_started_at = monotonic()
    try:
        initial_generation = await generate_requirements(db, project_id, session.id, provider, settings)
        await persist_requirements(
            db, project_id, session.id, initial_generation.batch, initial_generation.evidence_by_reference
        )
    except (LLMAASError, ValueError) as error:
        usage = provider.usage
        requirement_execution.status = "failed"
        requirement_execution.input_tokens = usage.input_tokens
        requirement_execution.output_tokens = usage.output_tokens
        requirement_execution.remaining_tokens = usage.remaining_tokens
        requirement_execution.duration_ms = round((monotonic() - requirement_started_at) * 1000)
        requirement_execution.error = str(error)
        session.status = "failed"
        await db.commit()
        return
    requirement_usage = provider.usage
    requirement_execution.status = "completed"
    requirement_execution.prompt_hash = initial_generation.prompt_hash
    requirement_execution.input_tokens = requirement_usage.input_tokens
    requirement_execution.output_tokens = requirement_usage.output_tokens
    requirement_execution.remaining_tokens = requirement_usage.remaining_tokens
    requirement_execution.duration_ms = round((monotonic() - requirement_started_at) * 1000)
    session.status = "processing_clarifications"
    session.current_node = "Clarification"

    execution = AgentExecution(
        session_id=session.id,
        node_name="Clarification",
        status="running",
        model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        batch = await generate_clarifications(db, project_id, session.id, provider, settings)
        question_ids = await persist_clarifications(db, session.id, batch)
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        execution.error = str(error)
        session.status = "failed"
        await db.commit()
        return
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        execution.error = str(error)
        session.status = "failed"
        await db.commit()
        return
    usage = provider.usage
    execution.status = "completed"
    execution.input_tokens = max(0, usage.input_tokens - requirement_usage.input_tokens)
    execution.output_tokens = max(0, usage.output_tokens - requirement_usage.output_tokens)
    execution.remaining_tokens = usage.remaining_tokens
    execution.duration_ms = round((monotonic() - started_at) * 1000)
    session.status = "awaiting_clarification"
    db.add(AuditEvent(project_id=project_id, action="session.created", entity_type="analysis_session", entity_id=session.id))
    await db.commit()
    await start_clarification_graph(ClarificationState(
        project_id=project_id,
        session_id=session.id,
        thread_id=session.thread_id,
        question_ids=question_ids,
        status="awaiting_clarification",
    ), settings.checkpoint_database_path)


@router.post("/projects/{project_id}/sessions", response_model=AnalysisSessionRead, status_code=status.HTTP_201_CREATED)
async def create_analysis_session(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> AnalysisSession:
    if await db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    existing = await db.scalar(select(AnalysisSession).where(
        AnalysisSession.project_id == project_id,
        AnalysisSession.status.in_(("processing_requirements", "processing_clarifications", "awaiting_clarification")),
    ).order_by(AnalysisSession.created_at.desc()))
    if existing:
        return existing
    session = AnalysisSession(
        project_id=project_id, thread_id=str(uuid4()),
        status="processing_requirements", current_node="Requirement",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    background_tasks.add_task(prepare_analysis_session, project_id, session.id, db, settings, provider)
    return session


@router.get("/sessions/{session_id}", response_model=AnalysisSessionRead)
async def get_analysis_session(session_id: str, db: AsyncSession = Depends(get_session)) -> AnalysisSession:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    return session


@router.get("/sessions/{session_id}/clarifications/next", response_model=ClarificationRead)
async def next_clarification(session_id: str, db: AsyncSession = Depends(get_session)) -> ClarificationRead:
    clarification = (await db.execute(
        select(Clarification)
        .where(Clarification.session_id == session_id, Clarification.status == "pending")
        .order_by(Clarification.created_at, Clarification.id)
        .limit(1)
    )).scalar_one_or_none()
    if clarification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No pending clarification")
    options = (await db.execute(
        select(ClarificationOption)
        .where(ClarificationOption.clarification_id == clarification.id)
        .order_by(ClarificationOption.position)
    )).scalars().all()
    return ClarificationRead(
        id=clarification.id,
        session_id=session_id,
        requirement_id=clarification.requirement_stable_id,
        question=clarification.question,
        reason=clarification.reason,
        severity=clarification.severity,
        missing_field=clarification.missing_field,
        recommended_answer_type=clarification.recommended_answer_type,
        blocking=clarification.blocking,
        required=clarification.required,
        recommended_option_id=clarification.recommended_option_id or "",
        allow_custom_answer=clarification.allow_custom_answer,
        source_references=json.loads(clarification.source_references_json),
        options=[ClarificationOptionRead(id=option.id, label=option.label, position=option.position) for option in options],
    )


@router.get("/sessions/{session_id}/clarifications", response_model=list[ClarificationHistoryRead])
async def clarification_history(
    session_id: str,
    db: AsyncSession = Depends(get_session),
) -> list[ClarificationHistoryRead]:
    if await db.get(AnalysisSession, session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    rows = (await db.execute(
        select(Clarification, ClarificationAnswer, ClarificationOption)
        .outerjoin(ClarificationAnswer, ClarificationAnswer.clarification_id == Clarification.id)
        .outerjoin(ClarificationOption, ClarificationOption.id == ClarificationAnswer.option_id)
        .where(Clarification.session_id == session_id)
        .order_by(Clarification.created_at, Clarification.id)
    )).all()
    return [ClarificationHistoryRead(
        id=clarification.id,
        requirement_id=clarification.requirement_stable_id,
        question=clarification.question,
        severity=clarification.severity,
        status=clarification.status,
        action=answer.action if answer else None,
        answer=(answer.custom_answer or (option.label if option else None)) if answer else None,
        answered_at=answer.created_at if answer else None,
    ) for clarification, answer, option in rows]


AGENT_NAMES = {
    "Intake", "Document Analysis", "Clarification", "Requirement", "Decomposition",
    "Backlog", "Enrichment", "Estimation", "Dependency", "Planning Data",
    "Assignment", "Sprint Planning", "Duplicate Detection", "Quality",
    "Board Health", "Human Approval", "Publisher",
}


@router.get("/sessions/{session_id}/agents/{agent_name}/messages", response_model=list[AgentMessageRead])
async def get_agent_messages(
    session_id: str,
    agent_name: str,
    db: AsyncSession = Depends(get_session),
) -> list[AgentMessageRead]:
    if await db.get(AnalysisSession, session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown agent")
    messages = (await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at, ChatMessage.id)
    )).scalars().all()
    result = []
    for message in messages:
        try:
            payload = json.loads(message.content)
        except ValueError:
            continue
        if payload.get("agent_name") == agent_name and isinstance(payload.get("content"), str):
            result.append(AgentMessageRead(
                id=message.id, agent_name=agent_name, role=message.role,
                content=payload["content"], created_at=message.created_at,
            ))
    return result


@router.post("/sessions/{session_id}/agents/{agent_name}/prompt", response_model=AgentPromptResult)
async def prompt_agent(
    session_id: str,
    agent_name: str,
    payload: AgentPromptCreate,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> AgentPromptResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if agent_name not in AGENT_NAMES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown agent")
    counts = {
        "requirements": await db.scalar(select(func.count(Requirement.id)).where(Requirement.session_id == session_id)) or 0,
        "decompositions": await db.scalar(select(func.count(Decomposition.id)).where(Decomposition.session_id == session_id)) or 0,
        "epics": await db.scalar(select(func.count(Epic.id)).where(Epic.session_id == session_id)) or 0,
        "stories": await db.scalar(select(func.count(UserStory.id)).where(UserStory.session_id == session_id)) or 0,
        "tasks": await db.scalar(select(func.count(Task.id)).where(Task.session_id == session_id)) or 0,
    }
    human_message = payload.message.strip()
    db.add(ChatMessage(
        session_id=session_id, role="human",
        content=json.dumps({"agent_name": agent_name, "content": human_message}),
    ))
    execution = AgentExecution(
        session_id=session_id, node_name=f"{agent_name} Feedback",
        status="running", model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    prompt = (
        f"You are the {agent_name} agent in a human-governed Scrum workflow. "
        "The human is reviewing this stage and supplied additional information or dissatisfaction. "
        "Return exactly one JSON object with this shape: "
        '{"understanding":"string","affected_artifacts":["string"],'
        '"needs_clarification":["string"],"revision_plan":["string"]}. '
        "Use empty arrays when no artifacts or clarifications apply. "
        "Do not claim that any artifact was changed, approved, or published. Do not invent project facts.\n\n"
        f"SESSION STATE: {session.status}; CURRENT NODE: {session.current_node}; ARTIFACT COUNTS: {json.dumps(counts)}\n\n"
        f"HUMAN MESSAGE:\n{human_message}"
    )
    try:
        raw_response = await provider.generate_text(prompt)
    except LLMAASError as error:
        execution.status = "failed"
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    try:
        feedback = AgentFeedbackDraft.model_validate_json(raw_response)
    except ValueError:
        repair_prompt = (
            "Your previous response did not match the required review schema. "
            "Return only one JSON object with exactly these four keys: "
            '"understanding" (string), "affected_artifacts" (array of strings), '
            '"needs_clarification" (array of strings), and "revision_plan" (non-empty array of strings). '
            "Use empty arrays where applicable. Do not add wrapper keys or markdown. "
            "Preserve the meaning of the previous response and do not invent project facts.\n\n"
            f"PREVIOUS RESPONSE:\n{raw_response}"
        )
        try:
            repaired_response = await provider.generate_text(repair_prompt)
            feedback = AgentFeedbackDraft.model_validate_json(repaired_response)
        except (LLMAASError, ValueError) as error:
            execution.status = "failed"
            execution.error = "Agent returned an invalid review response after one repair attempt"
            execution.duration_ms = round((monotonic() - started_at) * 1000)
            await db.commit()
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, execution.error) from error
    sections = [f"Understanding\n{feedback.understanding}"]
    if feedback.affected_artifacts:
        sections.append("Potentially affected artifacts\n" + "\n".join(f"- {item}" for item in feedback.affected_artifacts))
    if feedback.needs_clarification:
        sections.append("Clarification still needed\n" + "\n".join(f"- {item}" for item in feedback.needs_clarification))
    sections.append("Proposed revision plan\n" + "\n".join(f"- {item}" for item in feedback.revision_plan))
    response = "\n\n".join(sections)
    usage = provider.usage
    execution.status = "completed"
    execution.input_tokens = usage.input_tokens
    execution.output_tokens = usage.output_tokens
    execution.remaining_tokens = usage.remaining_tokens
    execution.duration_ms = round((monotonic() - started_at) * 1000)
    db.add(ChatMessage(
        session_id=session_id, role="assistant",
        content=json.dumps({"agent_name": agent_name, "content": response}),
    ))
    db.add(AuditEvent(
        project_id=session.project_id, actor="human", action="agent.feedback_requested",
        entity_type="analysis_session", entity_id=session.id,
        details_json=json.dumps({"agent_name": agent_name}),
    ))
    await db.commit()
    return AgentPromptResult(agent_name=agent_name, response=response, mutation_applied=False)


@router.post("/clarifications/{clarification_id}/answer", response_model=ClarificationAnswerResult)
async def answer_clarification(
    clarification_id: str,
    payload: ClarificationAnswerCreate,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ClarificationAnswerResult:
    clarification = await db.get(Clarification, clarification_id)
    if clarification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clarification not found")
    if clarification.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Clarification already answered")
    options = (await db.execute(
        select(ClarificationOption).where(ClarificationOption.clarification_id == clarification.id)
    )).scalars().all()
    option_ids = {option.id for option in options}
    option_id = payload.option_id
    custom_answer = payload.custom_answer.strip() if payload.custom_answer else None
    if payload.action == "selected" and option_id not in option_ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Select a valid option")
    if payload.action == "default":
        option_id = clarification.recommended_option_id
    if payload.action == "custom" and (not clarification.allow_custom_answer or not custom_answer):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A custom answer is not allowed or is empty")
    if payload.action == "skip" and clarification.blocking:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Blocking clarifications cannot be skipped; answer or mark unknown")

    session = await db.get(AnalysisSession, clarification.session_id)
    if session is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Analysis session not found")
    selected_label = next((option.label for option in options if option.id == option_id), None)
    answer_value = custom_answer or selected_label or payload.action
    db.add(ClarificationAnswer(
        clarification_id=clarification.id,
        option_id=option_id if payload.action in {"selected", "default"} else None,
        custom_answer=custom_answer if payload.action == "custom" else None,
        action=payload.action,
        provenance_json=ProvenanceValue(
            value=answer_value,
            origin="human_provided",
            confidence=1.0,
            requires_review=payload.action == "unknown",
        ).model_dump_json(),
    ))
    clarification.status = "answered" if payload.action != "skip" else "skipped"
    await db.commit()
    completed = await resume_clarification_graph(
        session.thread_id,
        {"clarification_id": clarification.id, "action": payload.action, "option_id": option_id, "custom_answer": custom_answer},
        settings.checkpoint_database_path,
    )
    has_next = (await db.execute(
        select(Clarification.id).where(Clarification.session_id == session.id, Clarification.status == "pending").limit(1)
    )).scalar_one_or_none() is not None
    if completed or not has_next:
        session.status = "clarifications_complete"
        session.current_node = "Requirement"
        await db.commit()
    return ClarificationAnswerResult(session_id=session.id, session_status=session.status, has_next=has_next)


@router.post("/sessions/{session_id}/generate", response_model=RequirementGenerationResult)
async def generate_session_requirements(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> RequirementGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "requirements_complete":
        existing = (await db.execute(
            select(Requirement).where(Requirement.session_id == session.id).order_by(Requirement.stable_id)
        )).scalars().all()
        return RequirementGenerationResult(
            session_id=session.id,
            session_status=session.status,
            requirements=[RequirementRead.model_validate(requirement_to_dict(item)) for item in existing],
        )
    if session.status != "clarifications_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete required clarifications before generation")

    execution = AgentExecution(
        session_id=session.id,
        node_name="Requirement",
        status="running",
        model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_requirements(db, session.project_id, session.id, provider, settings)
        await db.execute(delete(Requirement).where(Requirement.session_id == session.id))
        await db.flush()
        requirements = await persist_requirements(
            db, session.project_id, session.id, generation.batch, generation.evidence_by_reference
        )
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "requirements_complete"
        session.current_node = "Decomposition"
        db.add(AuditEvent(
            project_id=session.project_id,
            action="requirements.generated",
            entity_type="analysis_session",
            entity_id=session.id,
            details_json=json.dumps({"count": len(requirements)}),
        ))
        await db.commit()
        await checkpoint_requirement_stage(RequirementState(
            project_id=session.project_id,
            session_id=session.id,
            thread_id=session.thread_id,
            requirement_ids=[item.id for item in requirements],
            status="requirements_complete",
        ), settings.checkpoint_database_path)
        return RequirementGenerationResult(
            session_id=session.id,
            session_status=session.status,
            requirements=[RequirementRead.model_validate(requirement_to_dict(item)) for item in requirements],
        )
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/sessions/{session_id}/decompose", response_model=DecompositionGenerationResult)
async def decompose_session_requirements(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> DecompositionGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "decomposition_complete":
        existing = (await db.execute(
            select(Decomposition).where(Decomposition.session_id == session.id).order_by(Decomposition.stable_id)
        )).scalars().all()
        return DecompositionGenerationResult(
            session_id=session.id,
            session_status=session.status,
            decompositions=[DecompositionRead.model_validate(decomposition_to_dict(item)) for item in existing],
        )
    if session.status != "requirements_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete requirement generation before decomposition")

    execution = AgentExecution(
        session_id=session.id,
        node_name="Decomposition",
        status="running",
        model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_decompositions(db, session.id, provider)
        decompositions = await persist_decompositions(
            db, session.project_id, session.id, generation.batch
        )
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "decomposition_complete"
        session.current_node = "Backlog"
        db.add(AuditEvent(
            project_id=session.project_id,
            action="decomposition.generated",
            entity_type="analysis_session",
            entity_id=session.id,
            details_json=json.dumps({"count": len(decompositions)}),
        ))
        await db.commit()
        await checkpoint_decomposition_stage(DecompositionState(
            project_id=session.project_id,
            session_id=session.id,
            thread_id=session.thread_id,
            decomposition_ids=[item.id for item in decompositions],
            status="decomposition_complete",
        ), settings.checkpoint_database_path)
        return DecompositionGenerationResult(
            session_id=session.id,
            session_status=session.status,
            decompositions=[DecompositionRead.model_validate(decomposition_to_dict(item)) for item in decompositions],
        )
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/sessions/{session_id}/backlog", response_model=BacklogGenerationResult)
async def generate_session_backlog(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> BacklogGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "backlog_complete":
        epics = (await db.execute(
            select(Epic).where(Epic.session_id == session.id).order_by(Epic.stable_id)
        )).scalars().all()
        features = (await db.execute(
            select(Feature).where(Feature.session_id == session.id).order_by(Feature.stable_id)
        )).scalars().all()
        stories = (await db.execute(
            select(UserStory).where(UserStory.session_id == session.id).order_by(UserStory.stable_id)
        )).scalars().all()
        tasks = (await db.execute(
            select(Task).where(Task.session_id == session.id).order_by(Task.stable_id)
        )).scalars().all()
        epic_rows, feature_rows, story_rows, task_rows = backlog_to_dicts(epics, features, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
            features=[FeatureRead.model_validate(item) for item in feature_rows],
            stories=[StoryRead.model_validate(item) for item in story_rows],
            tasks=[TaskRead.model_validate(item) for item in task_rows],
        )
    retrying_failed_backlog = session.status == "failed" and session.current_node == "Backlog"
    if session.status != "decomposition_complete" and not retrying_failed_backlog:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete decomposition before backlog generation")
    if retrying_failed_backlog:
        session.status = "decomposition_complete"

    execution = AgentExecution(
        session_id=session.id,
        node_name="Backlog",
        status="running",
        model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_backlog(db, session.id, provider)
        epics, features, stories, tasks = await persist_backlog(
            db, session.project_id, session.id, generation.batch
        )
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "backlog_complete"
        session.current_node = "Enrichment"
        db.add(AuditEvent(
            project_id=session.project_id,
            action="backlog.generated",
            entity_type="analysis_session",
            entity_id=session.id,
            details_json=json.dumps({
                "epics": len(epics), "features": len(features), "stories": len(stories), "tasks": len(tasks),
            }),
        ))
        await db.commit()
        await checkpoint_backlog_stage(BacklogState(
            project_id=session.project_id,
            session_id=session.id,
            thread_id=session.thread_id,
            epic_ids=[item.id for item in epics],
            story_ids=[item.id for item in stories],
            task_ids=[item.id for item in tasks],
            status="backlog_complete",
        ), settings.checkpoint_database_path)
        epic_rows, feature_rows, story_rows, task_rows = backlog_to_dicts(epics, features, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
            features=[FeatureRead.model_validate(item) for item in feature_rows],
            stories=[StoryRead.model_validate(item) for item in story_rows],
            tasks=[TaskRead.model_validate(item) for item in task_rows],
        )
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/sessions/{session_id}/enrich", response_model=BacklogGenerationResult)
async def enrich_session_backlog(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> BacklogGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status not in {"backlog_complete", "enrichment_complete"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete backlog generation before enrichment")
    epics = (await db.execute(
        select(Epic).where(Epic.session_id == session.id).order_by(Epic.stable_id)
    )).scalars().all()
    features = (await db.execute(
        select(Feature).where(Feature.session_id == session.id).order_by(Feature.stable_id)
    )).scalars().all()
    stories = (await db.execute(
        select(UserStory).where(UserStory.session_id == session.id).order_by(UserStory.stable_id)
    )).scalars().all()
    tasks = (await db.execute(
        select(Task).where(Task.session_id == session.id).order_by(Task.stable_id)
    )).scalars().all()
    if session.status == "enrichment_complete":
        epic_rows, feature_rows, story_rows, task_rows = backlog_to_dicts(epics, features, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
            features=[FeatureRead.model_validate(item) for item in feature_rows],
            stories=[StoryRead.model_validate(item) for item in story_rows],
            tasks=[TaskRead.model_validate(item) for item in task_rows],
        )

    execution = AgentExecution(
        session_id=session.id, node_name="Enrichment", status="running", model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_enrichment(db, session.id, provider)
        epics, stories, tasks = await persist_enrichment(db, session.id, generation.batch)
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "enrichment_complete"
        session.current_node = "Estimation"
        db.add(AuditEvent(
            project_id=session.project_id, action="backlog.enriched",
            entity_type="analysis_session", entity_id=session.id,
            details_json=json.dumps({"epics": len(epics), "stories": len(stories), "tasks": len(tasks)}),
        ))
        await db.commit()
        await checkpoint_enrichment_stage(EnrichmentState(
            project_id=session.project_id, session_id=session.id,
            thread_id=session.thread_id, status="enrichment_complete",
        ), settings.checkpoint_database_path)
        epic_rows, feature_rows, story_rows, task_rows = backlog_to_dicts(epics, features, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
            features=[FeatureRead.model_validate(item) for item in feature_rows],
            stories=[StoryRead.model_validate(item) for item in story_rows],
            tasks=[TaskRead.model_validate(item) for item in task_rows],
        )
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("/sessions/{session_id}/dependency-order", response_model=EstimationBriefWorkspace)
@router.get("/sessions/{session_id}/estimation-brief", response_model=EstimationBriefWorkspace, include_in_schema=False)
async def get_estimation_brief(
    session_id: str,
    db: AsyncSession = Depends(get_session),
) -> EstimationBriefWorkspace:
    if await db.get(AnalysisSession, session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    record = await db.scalar(select(EstimationBrief).where(EstimationBrief.session_id == session_id))
    epics = (await db.execute(select(Epic).where(Epic.session_id == session_id).order_by(Epic.stable_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id))).scalars().all()
    dependencies = (await db.execute(select(Dependency).where(Dependency.session_id == session_id))).scalars().all()
    epic_by_story_id = {item.stable_id: item.epic_id for item in stories}
    epic_stable_by_id = {item.id: item.stable_id for item in epics}
    requirement_ids_by_epic = {item.stable_id: set(json.loads(item.requirement_ids_json)) for item in epics}
    dependency_conflicts = {
        frozenset((epic_stable_by_id[epic_by_story_id[item.source_stable_id]], epic_stable_by_id[epic_by_story_id[item.target_stable_id]]))
        for item in dependencies
        if item.source_stable_id in epic_by_story_id and item.target_stable_id in epic_by_story_id
        and epic_by_story_id[item.source_stable_id] != epic_by_story_id[item.target_stable_id]
    }
    parallel_groups: list[list[str]] = []
    for epic in epics:
        placed = False
        for group in parallel_groups:
            if all(
                not requirement_ids_by_epic[epic.stable_id] & requirement_ids_by_epic[member]
                and frozenset((epic.stable_id, member)) not in dependency_conflicts
                for member in group
            ):
                group.append(epic.stable_id)
                placed = True
                break
        if not placed:
            parallel_groups.append([epic.stable_id])
    return EstimationBriefWorkspace(
        brief=estimation_brief_to_read(record) if record else None,
        epics=[{
            "stable_id": item.stable_id, "title": item.title, "business_value": item.business_value,
            "architecture_layer": item.architecture_layer, "current_priority": item.priority,
        } for item in epics],
        parallel_groups=parallel_groups,
        parallelism_note=(
            "Parallel groups are calculated from analyzed story dependencies and non-overlapping requirement lineage. Human review remains required before sprint commitment."
            if dependencies else
            "Preliminary groups use non-overlapping requirement lineage. Run Dependency Analysis before accepting this ordering."
        ),
    )


@router.put("/sessions/{session_id}/dependency-order", response_model=EstimationBriefRead)
@router.put("/sessions/{session_id}/estimation-brief", response_model=EstimationBriefRead, include_in_schema=False)
async def save_estimation_brief(
    session_id: str,
    payload: EstimationBriefCreate,
    db: AsyncSession = Depends(get_session),
) -> EstimationBriefRead:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status not in {"estimation_complete", "dependencies_complete"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete estimation before recording the Dependency Epic order")
    epic_ids = set((await db.execute(select(Epic.stable_id).where(Epic.session_id == session_id))).scalars().all())
    supplied_epics = payload.ranked_epic_ids
    if len(supplied_epics) != len(set(supplied_epics)) or set(supplied_epics) != epic_ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Rank every generated Epic exactly once using supplied IDs")
    record = await db.scalar(select(EstimationBrief).where(EstimationBrief.session_id == session_id))
    answers = payload.model_dump(mode="json", exclude={"answered_by"})
    if record is None:
        record = EstimationBrief(
            session_id=session_id,
            answered_by=payload.answered_by,
            answers_json=json.dumps(answers),
        )
        db.add(record)
    else:
        record.answered_by = payload.answered_by
        record.answers_json = json.dumps(answers)
    db.add(AuditEvent(
        project_id=session.project_id,
        actor=payload.answered_by,
        action="dependency.epic_order_recorded",
        entity_type="analysis_session",
        entity_id=session.id,
        details_json=json.dumps({"fields": sorted(answers)}),
    ))
    await db.commit()
    await db.refresh(record)
    return estimation_brief_to_read(record)


@router.post("/sessions/{session_id}/estimate", response_model=BacklogGenerationResult)
async def estimate_session_backlog(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> BacklogGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status not in {"enrichment_complete", "estimation_complete"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete enrichment before estimation")
    epics = (await db.execute(select(Epic).where(Epic.session_id == session.id).order_by(Epic.stable_id))).scalars().all()
    features = (await db.execute(select(Feature).where(Feature.session_id == session.id).order_by(Feature.stable_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session.id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session.id).order_by(Task.stable_id))).scalars().all()
    if session.status == "estimation_complete":
        epic_rows, feature_rows, story_rows, task_rows = backlog_to_dicts(epics, features, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
            features=[FeatureRead.model_validate(item) for item in feature_rows],
            stories=[StoryRead.model_validate(item) for item in story_rows],
            tasks=[TaskRead.model_validate(item) for item in task_rows],
        )
    execution = AgentExecution(
        session_id=session.id, node_name="Estimation", status="running", model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_estimates(db, session.id, provider)
        stories, tasks = await persist_estimates(db, session.id, generation.batch)
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "estimation_complete"
        session.current_node = "Dependency"
        db.add(AuditEvent(
            project_id=session.project_id, action="backlog.estimated",
            entity_type="analysis_session", entity_id=session.id,
            details_json=json.dumps({"stories": len(stories), "tasks": len(tasks)}),
        ))
        await db.commit()
        await checkpoint_estimation_stage(EstimationState(
            project_id=session.project_id, session_id=session.id,
            thread_id=session.thread_id, status="estimation_complete",
        ), settings.checkpoint_database_path)
        epic_rows, feature_rows, story_rows, task_rows = backlog_to_dicts(epics, features, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
            features=[FeatureRead.model_validate(item) for item in feature_rows],
            stories=[StoryRead.model_validate(item) for item in story_rows],
            tasks=[TaskRead.model_validate(item) for item in task_rows],
        )
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/sessions/{session_id}/dependencies", response_model=DependencyGenerationResult)
async def analyze_session_dependencies(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> DependencyGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "dependencies_complete":
        existing = (await db.execute(
            select(Dependency).where(Dependency.session_id == session.id).order_by(Dependency.created_at)
        )).scalars().all()
        return DependencyGenerationResult(
            session_id=session.id, session_status=session.status,
            dependencies=[DependencyRead.model_validate(dependency_to_dict(item)) for item in existing],
        )
    if session.status != "estimation_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete estimation before dependency analysis")

    execution = AgentExecution(
        session_id=session.id, node_name="Dependency", status="running", model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_dependencies(db, session.id, provider)
        dependencies = await persist_dependencies(db, session.project_id, session.id, generation.batch)
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "dependencies_complete"
        session.current_node = "Assignment"
        db.add(AuditEvent(
            project_id=session.project_id, action="dependencies.analyzed",
            entity_type="analysis_session", entity_id=session.id,
            details_json=json.dumps({"count": len(dependencies)}),
        ))
        await db.commit()
        await checkpoint_dependency_stage(DependencyState(
            project_id=session.project_id, session_id=session.id, thread_id=session.thread_id,
            dependency_ids=[item.id for item in dependencies], status="dependencies_complete",
        ), settings.checkpoint_database_path)
        return DependencyGenerationResult(
            session_id=session.id, session_status=session.status,
            dependencies=[DependencyRead.model_validate(dependency_to_dict(item)) for item in dependencies],
        )
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("/planning-data/template")
async def download_planning_data_template() -> Response:
    return Response(
        content=build_planning_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Sprint-Sarthi-Planning-Data-Template.xlsx"'},
    )


@router.post("/sessions/{session_id}/planning-data", response_model=PlanningImportResult)
async def import_session_planning_data(
    session_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlanningImportResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status not in {"dependencies_complete", "planning_data_ready"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete dependency analysis before importing planning data")
    epic_count = await db.scalar(select(func.count(Epic.id)).where(Epic.session_id == session_id)) or 0
    if epic_count and await db.scalar(select(EstimationBrief).where(EstimationBrief.session_id == session_id)) is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Record the reviewed parallel Epic order before importing planning data")
    filename = Path(file.filename or "planning-data.xlsx").name
    if Path(filename).suffix.lower() != ".xlsx":
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Planning data must be an XLSX workbook")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    await file.close()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded planning workbook is empty")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds upload limit")
    try:
        parsed = parse_planning_workbook(content)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    requires_clarification = any(issue.blocking for issue in parsed.issues)
    if not requires_clarification:
        await persist_planning_workbook(db, session.project_id, filename, parsed)
        session.status = "planning_data_ready"
        session.current_node = "Assignment"
        db.add(AuditEvent(
            project_id=session.project_id, actor="human", action="planning_data.imported",
            entity_type="analysis_session", entity_id=session.id,
            details_json=json.dumps({
                "filename": filename, "members": len(parsed.members), "sprints": len(parsed.sprints),
                "holidays": len(parsed.holidays), "leaves": len(parsed.leaves),
            }),
        ))
        await db.commit()
    return PlanningImportResult(
        project_id=session.project_id, filename=filename,
        teams_imported=0 if requires_clarification else len(parsed.teams),
        members_imported=0 if requires_clarification else len(parsed.members),
        sprints_imported=0 if requires_clarification else len(parsed.sprints),
        holidays_imported=0 if requires_clarification else len(parsed.holidays),
        leaves_imported=0 if requires_clarification else len(parsed.leaves),
        requires_clarification=requires_clarification, issues=parsed.issues,
    )


@router.post("/sessions/{session_id}/assign", response_model=AssignmentGenerationResult)
async def assign_session_backlog(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> AssignmentGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "assignment_complete":
        existing = (await db.execute(
            select(AssignmentRecommendation)
            .where(AssignmentRecommendation.session_id == session.id)
            .order_by(AssignmentRecommendation.item_stable_id)
        )).scalars().all()
        rows = await assignments_to_dicts(db, existing)
        return AssignmentGenerationResult(
            session_id=session.id, session_status=session.status,
            assignments=[AssignmentRead.model_validate(item) for item in rows],
        )
    if session.status != "planning_data_ready":
        raise HTTPException(status.HTTP_409_CONFLICT, "Import verified planning data before assignment")

    execution = AgentExecution(
        session_id=session.id, node_name="Assignment", status="running", model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_assignments(db, session.project_id, session.id, provider)
        assignments = await persist_assignments(db, session.project_id, session.id, generation.batch)
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "assignment_complete"
        session.current_node = "Sprint"
        db.add(AuditEvent(
            project_id=session.project_id, action="assignments.recommended",
            entity_type="analysis_session", entity_id=session.id,
            details_json=json.dumps({"count": len(assignments), "status": "proposed"}),
        ))
        await db.commit()
        await checkpoint_assignment_stage(AssignmentState(
            project_id=session.project_id, session_id=session.id, thread_id=session.thread_id,
            assignment_ids=[item.id for item in assignments], status="assignment_complete",
        ), settings.checkpoint_database_path)
        rows = await assignments_to_dicts(db, assignments)
        return AssignmentGenerationResult(
            session_id=session.id, session_status=session.status,
            assignments=[AssignmentRead.model_validate(item) for item in rows],
        )
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        if str(error) == "Verified team capacity is insufficient for the estimated task hours":
            session.status = "dependencies_complete"
            session.current_node = "Planning Data"
            db.add(AuditEvent(
                project_id=session.project_id, action="planning_data.revision_requested",
                entity_type="analysis_session", entity_id=session.id,
                details_json=json.dumps({"reason": str(error)}),
            ))
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


async def sprint_scope_review_to_read(
    db: AsyncSession,
    session_id: str,
    review: SprintScopeReview | None,
) -> SprintScopeReviewRead:
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id).order_by(Task.stable_id))).scalars().all()
    story_by_id = {item.id: item for item in stories}
    selected_task_ids = json.loads(review.selected_task_ids_json) if review else [item.stable_id for item in tasks]
    selected_set = set(selected_task_ids)
    selected_story_ids = sorted({story_by_id[item.story_id].stable_id for item in tasks if item.stable_id in selected_set})
    return SprintScopeReviewRead(
        id=review.id if review else None, session_id=session_id,
        reviewed_by=review.reviewed_by if review else "",
        selected_task_ids=selected_task_ids,
        discarded_task_ids=json.loads(review.discarded_task_ids_json) if review else [],
        selected_story_ids=selected_story_ids, note=review.note if review else "",
        reviewed=review is not None,
        stories=[{
            "stable_id": story.stable_id, "title": story.title,
            "story_points": story.story_points or 0, "priority": story.priority,
            "selected": story.stable_id in selected_story_ids,
            "tasks": [{
                "stable_id": task.stable_id, "story_stable_id": story.stable_id,
                "title": task.title, "work_category": task.work_category,
                "estimated_hours": task.estimated_hours, "selected": task.stable_id in selected_set,
            } for task in tasks if task.story_id == story.id],
        } for story in stories],
    )


@router.get("/sessions/{session_id}/sprint-scope-review", response_model=SprintScopeReviewRead)
async def get_sprint_scope_review(session_id: str, db: AsyncSession = Depends(get_session)) -> SprintScopeReviewRead:
    if await db.get(AnalysisSession, session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    review = await db.scalar(select(SprintScopeReview).where(SprintScopeReview.session_id == session_id))
    return await sprint_scope_review_to_read(db, session_id, review)


@router.put("/sessions/{session_id}/sprint-scope-review", response_model=SprintScopeReviewRead)
async def save_sprint_scope_review(
    session_id: str,
    payload: SprintScopeReviewCreate,
    db: AsyncSession = Depends(get_session),
) -> SprintScopeReviewRead:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    reviewable_statuses = {
        "assignment_complete", "sprint_planning_complete", "duplicates_complete",
        "quality_clarification_required", "quality_complete", "awaiting_approval",
        "approved", "published",
    }
    if session.status not in reviewable_statuses:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete assignments before reviewing Sprint scope")
    tasks = (await db.execute(select(Task).where(Task.session_id == session_id))).scalars().all()
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session_id))).scalars().all()
    task_by_id = {item.stable_id: item for item in tasks}
    story_by_id = {item.id: item for item in stories}
    selected = payload.selected_task_ids
    if len(selected) != len(set(selected)) or not set(selected).issubset(task_by_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Selected Task scope contains duplicate or unknown IDs")
    selected_set = set(selected)
    existing_plans = (await db.execute(select(SprintPlanDecision).where(SprintPlanDecision.session_id == session_id))).scalars().all()
    committed_sprint_ids = set((await db.execute(select(Sprint.id).where(Sprint.project_id == session.project_id, Sprint.committed.is_(True)))).scalars().all())
    committed_sprint_id_values = {item.id for item in committed_sprint_ids}
    committed_story_ids = {
        item.story_id for item in existing_plans
        if item.decision == "planned" and item.sprint_id in committed_sprint_id_values
    }
    required_committed_tasks = {item.stable_id for item in tasks if item.story_id in committed_story_ids}
    if not required_committed_tasks.issubset(selected_set):
        raise HTTPException(status.HTTP_409_CONFLICT, "Tasks in committed Sprints cannot be discarded or re-sequenced")
    selected_story_ids = sorted({story_by_id[task_by_id[item_id].story_id].stable_id for item_id in selected})
    discarded_task_ids = sorted(set(task_by_id) - selected_set)
    selected_story_set = set(selected_story_ids)
    for task in tasks:
        task.status = "approved" if task.stable_id in selected_set else "discarded"
    for story in stories:
        story.status = "approved" if story.stable_id in selected_story_set else "discarded"
    review = await db.scalar(select(SprintScopeReview).where(SprintScopeReview.session_id == session_id))
    if review is None:
        review = SprintScopeReview(project_id=session.project_id, session_id=session_id, reviewed_by=payload.reviewed_by, selected_task_ids_json="[]", discarded_task_ids_json="[]", selected_story_ids_json="[]")
        db.add(review)
    review.reviewed_by = payload.reviewed_by
    review.selected_task_ids_json = json.dumps(sorted(selected_set))
    review.discarded_task_ids_json = json.dumps(discarded_task_ids)
    review.selected_story_ids_json = json.dumps(selected_story_ids)
    review.note = payload.note
    existing_sprint_items = {
        (item.sprint_id, item.story_id) for item in (await db.execute(select(SprintItem))).scalars().all()
    }
    for plan in existing_plans:
        key = (plan.sprint_id, plan.story_id)
        if plan.decision == "planned" and plan.sprint_id in committed_sprint_id_values and key not in existing_sprint_items:
            db.add(SprintItem(sprint_id=plan.sprint_id, story_id=plan.story_id, assignee_id=plan.assignee_id, reason=plan.reason))
    await db.execute(delete(SprintPlanDecision).where(SprintPlanDecision.session_id == session_id))
    await db.execute(delete(DuplicateCandidate).where(DuplicateCandidate.session_id == session_id))
    await db.execute(delete(QualityClarification).where(QualityClarification.session_id == session_id))
    await db.execute(delete(QualityResult).where(QualityResult.session_id == session_id))
    await db.execute(delete(BoardHealthResult).where(BoardHealthResult.session_id == session_id))
    await db.execute(delete(Approval).where(Approval.session_id == session_id))
    await db.execute(delete(Export).where(Export.session_id == session_id))
    recommendations = (await db.execute(select(AssignmentRecommendation).where(AssignmentRecommendation.session_id == session_id))).scalars().all()
    for recommendation in recommendations:
        recommendation.status = "proposed"
    session.status = "assignment_complete"
    session.current_node = "Sprint"
    db.add(AuditEvent(
        project_id=session.project_id, actor=payload.reviewed_by, action="sprint_scope.reviewed",
        entity_type="analysis_session", entity_id=session.id,
        details_json=json.dumps({"approved_tasks": len(selected_set), "discarded_tasks": len(discarded_task_ids), "approved_stories": len(selected_story_ids)}),
    ))
    await db.commit()
    await db.refresh(review)
    return await sprint_scope_review_to_read(db, session_id, review)


@router.post("/sessions/{session_id}/plan-sprints", response_model=SprintPlanningResult)
async def plan_session_sprints(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> SprintPlanningResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "sprint_planning_complete":
        existing = (await db.execute(
            select(SprintPlanDecision).where(SprintPlanDecision.session_id == session.id).order_by(SprintPlanDecision.created_at)
        )).scalars().all()
        rows = await sprint_plan_to_dicts(db, existing)
        completion, planned_points, available_capacity = await sprint_plan_forecast(db, session.project_id, session.id, existing)
        return SprintPlanningResult(
            session_id=session.id, session_status=session.status,
            decisions=[SprintDecisionRead.model_validate(item) for item in rows],
            ordering_heuristic=ORDERING_HEURISTIC, forecast_completion_date=completion,
            total_planned_points=planned_points, total_available_capacity_points=available_capacity,
        )
    if session.status != "assignment_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete assignment recommendations before sprint planning")
    if await db.scalar(select(SprintScopeReview).where(SprintScopeReview.session_id == session_id)) is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Review and approve the Task scope before sprint planning")
    execution = AgentExecution(
        session_id=session.id, node_name="Sprint", status="running", model=settings.llm_model,
    )
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_sprint_plan(db, session.project_id, session.id, provider)
        decisions = await persist_sprint_plan(db, session.project_id, session.id, generation.batch)
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "sprint_planning_complete"
        session.current_node = "Duplicate"
        db.add(AuditEvent(
            project_id=session.project_id, action="sprint_plan.recommended",
            entity_type="analysis_session", entity_id=session.id,
            details_json=json.dumps({"count": len(decisions), "status": "proposed"}),
        ))
        await db.commit()
        await checkpoint_sprint_planning_stage(SprintPlanningState(
            project_id=session.project_id, session_id=session.id, thread_id=session.thread_id,
            decision_ids=[item.id for item in decisions], status="sprint_planning_complete",
        ), settings.checkpoint_database_path)
        rows = await sprint_plan_to_dicts(db, decisions)
        completion, planned_points, available_capacity = await sprint_plan_forecast(db, session.project_id, session.id, decisions)
        return SprintPlanningResult(
            session_id=session.id, session_status=session.status,
            decisions=[SprintDecisionRead.model_validate(item) for item in rows],
            ordering_heuristic=ORDERING_HEURISTIC, forecast_completion_date=completion,
            total_planned_points=planned_points, total_available_capacity_points=available_capacity,
        )
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.error = str(error)
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/sessions/{session_id}/duplicates", response_model=DuplicateGenerationResult)
async def analyze_session_duplicates(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> DuplicateGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "duplicates_complete":
        existing = (await db.execute(select(DuplicateCandidate).where(DuplicateCandidate.session_id == session.id))).scalars().all()
        return DuplicateGenerationResult(session_id=session.id, session_status=session.status, candidates=[DuplicateRead.model_validate(duplicate_to_dict(item)) for item in existing])
    if session.status != "sprint_planning_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete sprint planning before duplicate analysis")
    execution = AgentExecution(session_id=session.id, node_name="Duplicate", status="running", model=settings.llm_model)
    db.add(execution)
    await db.commit()
    started_at = monotonic()
    try:
        generation = await generate_duplicates(db, session.id, provider)
        candidates = await persist_duplicates(db, session.project_id, session.id, generation.batch)
        usage = provider.usage
        execution.status = "completed"
        execution.prompt_hash = generation.prompt_hash
        execution.input_tokens = usage.input_tokens
        execution.output_tokens = usage.output_tokens
        execution.remaining_tokens = usage.remaining_tokens
        execution.duration_ms = round((monotonic() - started_at) * 1000)
        session.status = "duplicates_complete"
        session.current_node = "Quality"
        db.add(AuditEvent(project_id=session.project_id, action="duplicates.analyzed", entity_type="analysis_session", entity_id=session.id, details_json=json.dumps({"count": len(candidates)})))
        await db.commit()
        await checkpoint_duplicate_stage(DuplicateState(project_id=session.project_id, session_id=session.id, thread_id=session.thread_id, candidate_ids=[item.id for item in candidates], status="duplicates_complete"), settings.checkpoint_database_path)
        return DuplicateGenerationResult(session_id=session.id, session_status=session.status, candidates=[DuplicateRead.model_validate(duplicate_to_dict(item)) for item in candidates])
    except LLMAASError as error:
        usage = provider.usage
        execution.status = "failed"; execution.input_tokens = usage.input_tokens; execution.output_tokens = usage.output_tokens; execution.remaining_tokens = usage.remaining_tokens; execution.error = str(error); execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        usage = provider.usage
        execution.status = "failed"; execution.input_tokens = usage.input_tokens; execution.output_tokens = usage.output_tokens; execution.remaining_tokens = usage.remaining_tokens; execution.error = str(error); execution.duration_ms = round((monotonic() - started_at) * 1000)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/sessions/{session_id}/new-story-check", response_model=NewStoryCheckRead)
async def check_new_story_before_creation(
    session_id: str,
    payload: NewStoryCheckCreate,
    db: AsyncSession = Depends(get_session),
    provider: LLMProvider = Depends(get_llm_provider),
) -> NewStoryCheckRead:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    try:
        result = await assess_new_story(db, session.project_id, session.id, payload, provider)
    except LLMAASError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    record = NewStoryCheck(
        session_id=session.id, input_json=payload.model_dump_json(),
        result_json=result.assessment.model_dump_json(),
        status="awaiting_confirmation" if result.assessment.classification == "new" else result.assessment.classification,
    )
    db.add(record)
    db.add(AuditEvent(
        project_id=session.project_id, action="story.preflight_checked",
        entity_type="analysis_session", entity_id=session.id,
        details_json=json.dumps({"classification": result.assessment.classification, "prompt_hash": result.prompt_hash}),
    ))
    await db.commit()
    await db.refresh(record)
    return new_story_check_to_read(record)


@router.post("/sessions/{session_id}/stories", response_model=NewStoryCreateResult, status_code=status.HTTP_201_CREATED)
async def create_checked_story(
    session_id: str,
    payload: NewStoryConfirmCreate,
    db: AsyncSession = Depends(get_session),
) -> NewStoryCreateResult:
    session = await db.get(AnalysisSession, session_id)
    check = await db.get(NewStoryCheck, payload.check_id)
    if session is None or check is None or check.session_id != session_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "New-story check not found")
    assessment = NewStoryAssessment.model_validate_json(check.result_json)
    if check.status != "awaiting_confirmation" or assessment.classification != "new":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a genuinely new, explicitly confirmed story can be created")
    feature = await db.scalar(select(Feature).where(Feature.session_id == session_id, Feature.stable_id == assessment.suggested_feature_id))
    if feature is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "The suggested Feature is no longer available")
    proposal = NewStoryCheckCreate.model_validate_json(check.input_json)
    next_number = (await db.scalar(select(func.count(UserStory.id)))) or 0
    provenance = {
        field: ProvenanceValue(value=value, origin="human_provided", confidence=1.0, source_references=[], requires_review=False).model_dump(mode="json")
        for field, value in proposal.model_dump(mode="json").items()
    }
    story = UserStory(
        project_id=session.project_id, session_id=session.id, epic_id=feature.epic_id, feature_id=feature.id,
        stable_id=f"STORY-{next_number + 1:03d}", decomposition_ids_json="[]", requirement_ids_json="[]",
        title=proposal.title, user_story=proposal.user_story, description=proposal.description,
        acceptance_criteria=json.dumps(proposal.acceptance_criteria), definition_of_done_json=json.dumps(proposal.definition_of_done),
        priority=proposal.priority, story_points=proposal.story_points,
        source_references_json=json.dumps(proposal.source_references), provenance_json=json.dumps(provenance), status="draft",
    )
    db.add(story)
    check.status = "created"
    db.add(AuditEvent(
        project_id=session.project_id, actor="human", action="story.created_after_preflight",
        entity_type="user_story", entity_id=story.stable_id,
        details_json=json.dumps({"check_id": check.id, "suggested_sprint_id": assessment.suggested_sprint_id, "sprint_mutation_applied": False}),
    ))
    await db.commit()
    await db.refresh(story)
    return NewStoryCreateResult(
        check_id=check.id, story_id=story.id, story_stable_id=story.stable_id,
        suggested_sprint_id=assessment.suggested_sprint_id, sprint_mutation_applied=False,
    )


@router.post("/sessions/{session_id}/quality", response_model=QualityGenerationResult)
async def validate_session_quality(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QualityGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "quality_complete":
        existing = (await db.execute(select(QualityResult).where(QualityResult.session_id == session.id))).scalars().all()
        clarifications = (await db.execute(select(QualityClarification).where(QualityClarification.session_id == session.id))).scalars().all()
        return QualityGenerationResult(session_id=session.id, session_status=session.status, results=[QualityRead.model_validate(quality_to_dict(item)) for item in existing], clarifications=[QualityClarificationRead.model_validate(quality_clarification_to_dict(item)) for item in clarifications])
    if session.status == "quality_clarification_required":
        existing = (await db.execute(select(QualityResult).where(QualityResult.session_id == session.id))).scalars().all()
        clarifications = (await db.execute(select(QualityClarification).where(QualityClarification.session_id == session.id))).scalars().all()
        return QualityGenerationResult(session_id=session.id, session_status=session.status, results=[QualityRead.model_validate(quality_to_dict(item)) for item in existing], clarifications=[QualityClarificationRead.model_validate(quality_clarification_to_dict(item)) for item in clarifications])
    if session.status != "duplicates_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete duplicate analysis before quality validation")
    started_at = monotonic()
    execution = AgentExecution(session_id=session.id, node_name="Quality", status="running", model="deterministic-rules")
    db.add(execution)
    await db.flush()
    await db.execute(delete(QualityResult).where(QualityResult.session_id == session.id))
    results = await run_quality_checks(db, session.project_id, session.id)
    execution.status = "completed"
    execution.input_tokens = 0
    execution.output_tokens = 0
    execution.duration_ms = round((monotonic() - started_at) * 1000)
    failed = [item for item in results if item.score < QUALITY_THRESHOLD]
    clarifications = await create_quality_clarifications(db, session.id, results) if failed else []
    session.status = "quality_clarification_required" if failed else "quality_complete"
    session.current_node = "Quality" if failed else "BoardHealth"
    db.add(AuditEvent(project_id=session.project_id, action="quality.validated", entity_type="analysis_session", entity_id=session.id, details_json=json.dumps({"count": len(results), "failed": len(failed), "threshold": QUALITY_THRESHOLD})))
    await db.commit()
    if not failed:
        await checkpoint_validation_stage(ValidationState(project_id=session.project_id, session_id=session.id, thread_id=session.thread_id, status="quality_complete"), settings.checkpoint_database_path, "quality")
    return QualityGenerationResult(session_id=session.id, session_status=session.status, results=[QualityRead.model_validate(quality_to_dict(item)) for item in results], clarifications=[QualityClarificationRead.model_validate(quality_clarification_to_dict(item)) for item in clarifications])


@router.get("/sessions/{session_id}/quality-clarifications", response_model=list[QualityClarificationRead])
async def get_quality_clarifications(session_id: str, db: AsyncSession = Depends(get_session)) -> list[QualityClarificationRead]:
    if await db.get(AnalysisSession, session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    records = (await db.execute(select(QualityClarification).where(QualityClarification.session_id == session_id).order_by(QualityClarification.created_at))).scalars().all()
    return [QualityClarificationRead.model_validate(quality_clarification_to_dict(item)) for item in records]


@router.put("/quality-clarifications/{clarification_id}/answer", response_model=QualityClarificationRead)
async def answer_quality_clarification(
    clarification_id: str,
    payload: QualityClarificationAnswerCreate,
    db: AsyncSession = Depends(get_session),
) -> QualityClarificationRead:
    clarification = await db.get(QualityClarification, clarification_id)
    if clarification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quality clarification not found")
    if clarification.status == "answered":
        return QualityClarificationRead.model_validate(quality_clarification_to_dict(clarification))
    model = {"epic": Epic, "feature": Feature, "story": UserStory, "task": Task}[clarification.item_type]
    item = await db.scalar(select(model).where(model.session_id == clarification.session_id, model.stable_id == clarification.item_id))
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Backlog item not found")
    try:
        apply_quality_clarification(item, clarification.item_type, json.loads(clarification.missing_fields_json), payload.values)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    clarification.answer_json = json.dumps(payload.values)
    clarification.status = "answered"
    session = await db.get(AnalysisSession, clarification.session_id)
    pending = await db.scalar(select(func.count(QualityClarification.id)).where(QualityClarification.session_id == clarification.session_id, QualityClarification.status == "pending", QualityClarification.id != clarification.id))
    if session and not pending:
        session.status = "duplicates_complete"
        session.current_node = "Quality"
    if session:
        db.add(AuditEvent(project_id=session.project_id, actor="human", action="quality.clarification_answered", entity_type=clarification.item_type, entity_id=clarification.item_id, details_json=json.dumps({"fields": sorted(payload.values)})))
    await db.commit()
    await db.refresh(clarification)
    return QualityClarificationRead.model_validate(quality_clarification_to_dict(clarification))


@router.get("/sessions/{session_id}/board-health", response_model=BoardHealthGenerationResult)
async def get_session_board_health(
    session_id: str,
    db: AsyncSession = Depends(get_session),
) -> BoardHealthGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status not in {"awaiting_approval", "approved", "published"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete board health assessment before viewing board health")
    health = await run_board_health(db, session.project_id, session.id)
    await db.commit()
    return BoardHealthGenerationResult(
        session_id=session.id,
        session_status=session.status,
        health=BoardHealthRead.model_validate(board_health_to_dict(health)),
    )


@router.post("/sessions/{session_id}/board-health", response_model=BoardHealthGenerationResult)
async def assess_session_board_health(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BoardHealthGenerationResult:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "awaiting_approval":
        health = await run_board_health(db, session.project_id, session.id)
        await db.commit()
        return BoardHealthGenerationResult(session_id=session.id, session_status=session.status, health=BoardHealthRead.model_validate(board_health_to_dict(health)))
    if session.status != "quality_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete quality validation before board health assessment")
    started_at = monotonic()
    execution = AgentExecution(session_id=session.id, node_name="BoardHealth", status="running", model="deterministic-rules")
    db.add(execution)
    await db.flush()
    health = await run_board_health(db, session.project_id, session.id)
    execution.status = "completed"
    execution.input_tokens = 0
    execution.output_tokens = 0
    execution.duration_ms = round((monotonic() - started_at) * 1000)
    session.status = "awaiting_approval"
    session.current_node = "HumanApproval"
    db.add(AuditEvent(project_id=session.project_id, action="board_health.assessed", entity_type="analysis_session", entity_id=session.id, details_json=json.dumps({"score": health.score, "risk_level": health.risk_level})))
    await db.commit()
    await checkpoint_validation_stage(ValidationState(project_id=session.project_id, session_id=session.id, thread_id=session.thread_id, status="awaiting_approval"), settings.checkpoint_database_path, "board_health")
    return BoardHealthGenerationResult(session_id=session.id, session_status=session.status, health=BoardHealthRead.model_validate(board_health_to_dict(health)))


@router.post("/sessions/{session_id}/approval", response_model=ApprovalDecisionRead)
async def decide_session_approval(
    session_id: str,
    payload: ApprovalDecisionCreate,
    db: AsyncSession = Depends(get_session),
) -> ApprovalDecisionRead:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status != "awaiting_approval":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete board health assessment before human approval")
    approval = Approval(
        project_id=session.project_id, session_id=session.id, action="publish_backlog",
        approved_by=payload.approved_by.strip(), decision=payload.decision, note=payload.note.strip(),
    )
    db.add(approval)
    if payload.decision == "approve":
        session.status = "approved"
        session.current_node = "Publisher"
        recommendations = (await db.execute(select(AssignmentRecommendation).where(AssignmentRecommendation.session_id == session.id))).scalars().all()
        plans = (await db.execute(select(SprintPlanDecision).where(SprintPlanDecision.session_id == session.id))).scalars().all()
        for item in recommendations:
            item.status = "approved"
        for item in plans:
            item.status = "approved"
        sprint_ids = {item.sprint_id for item in plans if item.decision == "planned" and item.sprint_id}
        if sprint_ids:
            planned_sprints = (await db.execute(select(Sprint).where(Sprint.id.in_(sprint_ids)))).scalars().all()
            for sprint in planned_sprints:
                sprint.committed = True
    else:
        session.status = "review_rejected" if payload.decision == "reject" else "changes_requested"
        session.current_node = "HumanApproval"
    db.add(AuditEvent(
        project_id=session.project_id, actor=payload.approved_by.strip(), action=f"review.{payload.decision}",
        entity_type="analysis_session", entity_id=session.id,
        details_json=json.dumps({"note": payload.note.strip()}),
    ))
    await db.commit()
    await db.refresh(approval)
    return ApprovalDecisionRead(
        id=approval.id, session_id=session.id, decision=approval.decision,
        approved_by=approval.approved_by, note=approval.note, session_status=session.status,
    )


@router.post("/sessions/{session_id}/publish", response_model=ExportRead)
async def publish_session(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ExportRead:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    if session.status == "published":
        existing = await db.scalar(select(Export).where(Export.session_id == session.id, Export.status == "completed"))
        if existing:
            return ExportRead(id=existing.id, session_id=session.id, filename="sprint_sarthi_backlog.xlsx", sha256=existing.sha256, status=existing.status, download_url=f"/api/v1/exports/{existing.id}/download")
    approval = await db.scalar(select(Approval).where(Approval.session_id == session.id, Approval.decision == "approve").order_by(Approval.created_at.desc()))
    if session.status != "approved" or approval is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Explicit human approval is required before publication")
    destination = settings.export_dir / session.project_id / session.id / "sprint_sarthi_backlog.xlsx"
    export = Export(project_id=session.project_id, session_id=session.id, approval_id=approval.id, filename=str(destination), sha256="", status="generating")
    db.add(export)
    await db.flush()
    try:
        export.sha256 = await publish_session_workbook(db, session, destination)
        export.status = "completed"
        session.status = "published"
        session.current_node = "Complete"
        db.add(AuditEvent(project_id=session.project_id, actor=approval.approved_by, action="workbook.published", entity_type="export", entity_id=export.id, details_json=json.dumps({"filename": "sprint_sarthi_backlog.xlsx", "sha256": export.sha256})))
        await db.commit()
    except Exception as error:
        export.status = "failed"
        await db.commit()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Workbook publication validation failed") from error
    return ExportRead(id=export.id, session_id=session.id, filename="sprint_sarthi_backlog.xlsx", sha256=export.sha256, status=export.status, download_url=f"/api/v1/exports/{export.id}/download")


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str,
    db: AsyncSession = Depends(get_session),
) -> FileResponse:
    export = await db.get(Export, export_id)
    if export is None or export.status != "completed":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Completed export not found")
    path = Path(export.filename)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Export file is unavailable")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="sprint_sarthi_backlog.xlsx")


@router.get("/sessions/{session_id}/published-workbook", response_model=WorkbookPreviewRead)
async def preview_published_workbook(
    session_id: str,
    sheet: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=250),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    session = await db.get(AnalysisSession, session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    export = await db.scalar(select(Export).where(Export.session_id == session.id, Export.status == "completed"))
    if export is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Published workbook not found")
    path = Path(export.filename)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Published workbook file is unavailable")
    try:
        preview = preview_workbook(path, sheet, offset, limit)
    except ValueError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    return {"export_id": export.id, "filename": path.name, **preview}


@router.get("/sessions/{session_id}/usage", response_model=SessionUsageRead)
async def get_session_usage(session_id: str, db: AsyncSession = Depends(get_session)) -> SessionUsageRead:
    if await db.get(AnalysisSession, session_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis session not found")
    executions = (await db.execute(
        select(AgentExecution)
        .where(AgentExecution.session_id == session_id)
        .order_by(AgentExecution.created_at, AgentExecution.id)
    )).scalars().all()
    input_tokens = sum(execution.input_tokens or 0 for execution in executions)
    output_tokens = sum(execution.output_tokens or 0 for execution in executions)
    remaining_tokens = next(
        (execution.remaining_tokens for execution in reversed(executions) if execution.remaining_tokens is not None),
        None,
    )
    return SessionUsageRead(
        session_id=session_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        remaining_tokens=remaining_tokens,
        remaining_reported=remaining_tokens is not None,
        executions=[AgentUsageRead(
            node_name=execution.node_name,
            model=execution.model,
            input_tokens=execution.input_tokens or 0,
            output_tokens=execution.output_tokens or 0,
            total_tokens=(execution.input_tokens or 0) + (execution.output_tokens or 0),
            remaining_tokens=execution.remaining_tokens,
            duration_ms=execution.duration_ms,
            created_at=execution.created_at,
        ) for execution in executions],
    )


@router.get("/logs", response_model=OperationalLogsRead)
async def get_operational_logs(
    project_id: str | None = Query(default=None),
    kind: str = Query(default="all", pattern="^(all|audit|execution)$"),
    limit: int = Query(default=300, ge=1, le=1000),
    db: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    projects = (await db.execute(select(Project).order_by(Project.name))).scalars().all()
    project_by_id = {item.id: item for item in projects}
    sessions = (await db.execute(select(AnalysisSession))).scalars().all()
    session_by_id = {item.id: item for item in sessions}
    entries: list[dict[str, object]] = []

    if kind in {"all", "audit"}:
        audit_query = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        if project_id:
            audit_query = audit_query.where(AuditEvent.project_id == project_id)
        audits = (await db.execute(audit_query)).scalars().all()
        for item in audits:
            try:
                details = json.loads(item.details_json or "{}")
            except json.JSONDecodeError:
                details = {}
            safe_details = {
                str(key): value for key, value in details.items()
                if not any(secret in str(key).lower() for secret in ("secret", "password", "token", "api_key", "credential"))
                and isinstance(value, (str, int, float, bool, type(None)))
            }
            entries.append({
                "id": item.id, "kind": "audit", "created_at": item.created_at,
                "project_id": item.project_id,
                "project_name": project_by_id[item.project_id].name if item.project_id in project_by_id else "Deleted project",
                "session_id": item.entity_id if item.entity_type == "analysis_session" else None,
                "source": item.actor, "status": "recorded", "message": item.action,
                "metadata": {"entity_type": item.entity_type, "entity_id": item.entity_id, **safe_details},
            })

    if kind in {"all", "execution"}:
        execution_query = select(AgentExecution)
        if project_id:
            execution_query = execution_query.join(
                AnalysisSession, AgentExecution.session_id == AnalysisSession.id
            ).where(AnalysisSession.project_id == project_id)
        execution_query = execution_query.order_by(AgentExecution.created_at.desc()).limit(limit)
        executions = (await db.execute(execution_query)).scalars().all()
        for item in executions:
            session = session_by_id.get(item.session_id)
            resolved_project_id = session.project_id if session else None
            entries.append({
                "id": item.id, "kind": "execution", "created_at": item.created_at,
                "project_id": resolved_project_id,
                "project_name": project_by_id[resolved_project_id].name if resolved_project_id in project_by_id else "Deleted project",
                "session_id": item.session_id, "source": item.node_name, "status": item.status,
                "message": f"{item.node_name} agent {item.status}",
                "metadata": {
                    "model": item.model, "duration_ms": item.duration_ms,
                    "input_tokens": item.input_tokens, "output_tokens": item.output_tokens,
                    "remaining_tokens": item.remaining_tokens, "prompt_hash": item.prompt_hash,
                    "error": item.error[:500] if item.error else None,
                },
            })

    entries.sort(key=lambda item: item["created_at"], reverse=True)
    return {
        "entries": entries[:limit],
        "projects": [{"id": item.id, "name": item.name} for item in projects],
    }


@router.get("/backlog/{item_type}/{item_id}/sources", response_model=BacklogSourcesRead)
async def get_backlog_item_sources(
    item_type: BacklogItemType = ApiPath(),
    item_id: str = ApiPath(min_length=36, max_length=36),
    db: AsyncSession = Depends(get_session),
) -> BacklogSourcesRead:
    resolution = await resolve_item_evidence(db, item_type, item_id)
    if resolution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Backlog item not found")
    return BacklogSourcesRead(
        item_id=item_id,
        item_type=item_type,
        sources=resolution.sources,
        unresolved_references=resolution.unresolved_references,
    )
