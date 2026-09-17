import asyncio
import json
from pathlib import Path
from time import monotonic
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Path as ApiPath, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.models.entities import (
    AgentExecution, AnalysisSession, Approval, AssignmentRecommendation, AuditEvent, BoardHealthResult, Clarification, ClarificationAnswer,
    ClarificationOption, Decomposition, Dependency, Document, DocumentSection, DuplicateCandidate, Epic, Job, Project, Requirement,
    Export, QualityResult, Sprint, SprintPlanDecision, Task, UserStory,
)
from app.providers import get_llm_provider
from app.providers.base import LLMProvider
from app.providers.llmaas import LLMAASError
from app.schemas.clarifications import (
    AnalysisSessionRead, ClarificationAnswerCreate, ClarificationAnswerResult,
    ClarificationOptionRead, ClarificationRead,
)
from app.schemas.backlog import BacklogGenerationResult, EpicRead, StoryRead, TaskRead
from app.schemas.evidence import BacklogItemType, BacklogSourcesRead
from app.schemas.decomposition import DecompositionGenerationResult, DecompositionRead
from app.schemas.dependencies import DependencyGenerationResult, DependencyRead
from app.schemas.duplicates import DuplicateGenerationResult, DuplicateRead
from app.schemas.projects import DocumentChunkRead, DocumentRead, JobRead, ProjectCreate, ProjectRead
from app.schemas.planning_data import AssignmentGenerationResult, AssignmentRead, PlanningImportResult
from app.schemas.sprint_planning import SprintDecisionRead, SprintPlanningResult
from app.schemas.quality import BoardHealthGenerationResult, BoardHealthRead, QualityGenerationResult, QualityRead
from app.schemas.approval import ApprovalDecisionCreate, ApprovalDecisionRead, ExportRead
from app.schemas.requirements import RequirementGenerationResult, RequirementRead
from app.schemas.provenance import ProvenanceValue
from app.schemas.usage import AgentUsageRead, SessionUsageRead
from app.services.document_extraction import DocumentExtractionError, extract_document
from app.services.backlog import backlog_to_dicts, generate_backlog, persist_backlog
from app.services.enrichment import generate_enrichment, persist_enrichment
from app.services.estimation import generate_estimates, persist_estimates
from app.services.dependencies import dependency_to_dict, generate_dependencies, persist_dependencies
from app.services.duplicates import duplicate_to_dict, generate_duplicates, persist_duplicates
from app.services.decomposition import decomposition_to_dict, generate_decompositions, persist_decompositions
from app.services.evidence import resolve_item_evidence
from app.services.clarifications import generate_clarifications, persist_clarifications
from app.services.uploads import save_upload
from app.services.requirements import generate_requirements, persist_requirements, requirement_to_dict
from app.services.planning_data import parse_planning_workbook, persist_planning_workbook
from app.services.assignment import assignments_to_dicts, generate_assignments, persist_assignments
from app.services.sprint_planning import generate_sprint_plan, persist_sprint_plan, sprint_plan_to_dicts
from app.services.quality import board_health_to_dict, quality_to_dict, run_board_health, run_quality_checks
from app.services.publication import publish_session_workbook
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


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_session)) -> Project:
    project = Project(name=payload.name.strip(), description=payload.description.strip())
    db.add(project)
    await db.flush()
    db.add(AuditEvent(project_id=project.id, action="project.created", entity_type="project", entity_id=project.id))
    await db.commit()
    await db.refresh(project)
    return project


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
    ) for chunk in chunks]


@router.post("/projects/{project_id}/sessions", response_model=AnalysisSessionRead, status_code=status.HTTP_201_CREATED)
async def create_analysis_session(
    project_id: str,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_llm_provider),
) -> AnalysisSession:
    if await db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    session = AnalysisSession(
        project_id=project_id,
        thread_id=str(uuid4()),
        status="processing_requirements",
        current_node="Requirement",
    )
    db.add(session)
    await db.flush()
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
        error_status = status.HTTP_502_BAD_GATEWAY if isinstance(error, LLMAASError) else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(error_status, str(error)) from error
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
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
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
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
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
    await db.refresh(session)
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
        stories = (await db.execute(
            select(UserStory).where(UserStory.session_id == session.id).order_by(UserStory.stable_id)
        )).scalars().all()
        tasks = (await db.execute(
            select(Task).where(Task.session_id == session.id).order_by(Task.stable_id)
        )).scalars().all()
        epic_rows, story_rows, task_rows = backlog_to_dicts(epics, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
            stories=[StoryRead.model_validate(item) for item in story_rows],
            tasks=[TaskRead.model_validate(item) for item in task_rows],
        )
    if session.status != "decomposition_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete decomposition before backlog generation")

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
        epics, stories, tasks = await persist_backlog(
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
                "epics": len(epics), "stories": len(stories), "tasks": len(tasks),
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
        epic_rows, story_rows, task_rows = backlog_to_dicts(epics, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
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
    stories = (await db.execute(
        select(UserStory).where(UserStory.session_id == session.id).order_by(UserStory.stable_id)
    )).scalars().all()
    tasks = (await db.execute(
        select(Task).where(Task.session_id == session.id).order_by(Task.stable_id)
    )).scalars().all()
    if session.status == "enrichment_complete":
        epic_rows, story_rows, task_rows = backlog_to_dicts(epics, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
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
        epic_rows, story_rows, task_rows = backlog_to_dicts(epics, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
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
    stories = (await db.execute(select(UserStory).where(UserStory.session_id == session.id).order_by(UserStory.stable_id))).scalars().all()
    tasks = (await db.execute(select(Task).where(Task.session_id == session.id).order_by(Task.stable_id))).scalars().all()
    if session.status == "estimation_complete":
        epic_rows, story_rows, task_rows = backlog_to_dicts(epics, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
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
        epic_rows, story_rows, task_rows = backlog_to_dicts(epics, stories, tasks)
        return BacklogGenerationResult(
            session_id=session.id, session_status=session.status,
            epics=[EpicRead.model_validate(item) for item in epic_rows],
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
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


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
        return SprintPlanningResult(
            session_id=session.id, session_status=session.status,
            decisions=[SprintDecisionRead.model_validate(item) for item in rows],
        )
    if session.status != "assignment_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete assignment recommendations before sprint planning")
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
        return SprintPlanningResult(
            session_id=session.id, session_status=session.status,
            decisions=[SprintDecisionRead.model_validate(item) for item in rows],
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
        return QualityGenerationResult(session_id=session.id, session_status=session.status, results=[QualityRead.model_validate(quality_to_dict(item)) for item in existing])
    if session.status != "duplicates_complete":
        raise HTTPException(status.HTTP_409_CONFLICT, "Complete duplicate analysis before quality validation")
    started_at = monotonic()
    execution = AgentExecution(session_id=session.id, node_name="Quality", status="running", model="deterministic-rules")
    db.add(execution)
    await db.flush()
    results = await run_quality_checks(db, session.project_id, session.id)
    execution.status = "completed"
    execution.input_tokens = 0
    execution.output_tokens = 0
    execution.duration_ms = round((monotonic() - started_at) * 1000)
    session.status = "quality_complete"
    session.current_node = "BoardHealth"
    db.add(AuditEvent(project_id=session.project_id, action="quality.validated", entity_type="analysis_session", entity_id=session.id, details_json=json.dumps({"count": len(results), "failed": sum(item.score < 80 for item in results)})))
    await db.commit()
    await checkpoint_validation_stage(ValidationState(project_id=session.project_id, session_id=session.id, thread_id=session.thread_id, status="quality_complete"), settings.checkpoint_database_path, "quality")
    return QualityGenerationResult(session_id=session.id, session_status=session.status, results=[QualityRead.model_validate(quality_to_dict(item)) for item in results])


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
        existing = await db.scalar(select(BoardHealthResult).where(BoardHealthResult.session_id == session.id))
        if existing:
            return BoardHealthGenerationResult(session_id=session.id, session_status=session.status, health=BoardHealthRead.model_validate(board_health_to_dict(existing)))
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
