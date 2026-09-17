"use client";

import { ChangeEvent, FormEvent, useEffect, useState, useSyncExternalStore } from "react";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Coins,
  FileText,
  GitBranch,
  Loader2,
  Plus,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { Traceability } from "@/components/Traceability";

type Project = { id: string; name: string; status: string };
type Document = {
  id: string;
  original_name: string;
  size_bytes: number;
  status: string;
};
type AnalysisJob = {
  id: string;
  status: string;
  progress: number;
  error: string | null;
};
type AnalysisSession = { id: string; thread_id: string; status: string };
type LLMUsage = {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  remaining_tokens: number | null;
  remaining_reported: boolean;
};
type Clarification = {
  id: string;
  requirement_id: string;
  question: string;
  reason: string;
  severity: "critical" | "high" | "medium" | "low";
  missing_field: string;
  recommended_answer_type: string;
  blocking: boolean;
  required: boolean;
  recommended_option_id: string;
  allow_custom_answer: boolean;
  source_references: string[];
  options: { id: string; label: string; position: number }[];
};
type Requirement = {
  id: string;
  stable_id: string;
  title: string;
  description: string;
  category: string;
  requirement_status: string;
  actors: string[];
  systems: string[];
  priority: string;
  acceptance_criteria: string[];
  source_references: string[];
  confidence: number;
  requires_clarification: boolean;
  clarification_reasons: string[];
};
type Decomposition = {
  id: string;
  stable_id: string;
  requirement_ids: string[];
  parent_capability: string;
  component_type: string;
  title: string;
  description: string;
  suggested_backlog_level: string;
  rationale: string;
  source_references: string[];
  confidence: number;
};
type BacklogEpic = {
  id: string;
  stable_id: string;
  title: string;
  description: string;
  business_value: string;
  priority: string;
  acceptance_criteria?: string[];
  source_references: string[];
};
type BacklogStory = {
  id: string;
  stable_id: string;
  epic_stable_id: string;
  title: string;
  user_story: string;
  priority: string;
  acceptance_criteria: string[];
  story_points: number | null;
  estimation_rationale: string;
  source_references: string[];
};
type BacklogTask = {
  id: string;
  stable_id: string;
  story_stable_id: string;
  title: string;
  description: string;
  task_type: string;
  estimated_hours: number | null;
  estimation_rationale: string;
  source_references: string[];
};
type Backlog = {
  epics: BacklogEpic[];
  stories: BacklogStory[];
  tasks: BacklogTask[];
};
type BacklogDependency = {
  id: string;
  source_stable_id: string;
  target_stable_id: string;
  dependency_type: string;
  risk: string;
  explanation: string;
  confidence: number;
};
type PlanningIssue = {
  sheet: string;
  row: number | null;
  field: string;
  message: string;
  blocking: boolean;
};
type Assignment = {
  id: string;
  item_stable_id: string;
  team_member_name: string;
  role: string;
  department: string;
  recommended_hours: number | null;
  match_score: number;
  reason: string;
  confidence: number;
  status: string;
};
type SprintDecision = {
  id: string;
  story_stable_id: string;
  story_title: string;
  story_points: number;
  decision: string;
  sprint_name: string | null;
  assignee_name: string | null;
  reason: string;
  status: string;
};
type DuplicateCandidate = {
  id: string;
  source_stable_id: string;
  target_stable_id: string;
  similarity: number;
  recommendation: string;
  rationale: string;
};
type QualityResult = { id: string; item_id: string; item_type: string; score: number; passed: boolean; issues: string[] };
type BoardHealth = { score: number; risk_level: string; metrics: Record<string, number>; issues: string[]; status: string };
type PublishedExport = { filename: string; sha256: string; download_url: string };
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const stages = [
  "Intake",
  "Clarify",
  "Generate",
  "Review",
  "Plan",
  "Approve",
  "Export",
];
const stageHeadings = [
  "Project intake",
  "Clarification",
  "Generate backlog",
  "Review backlog",
  "Sprint planning",
  "Human approval",
  "Workbook export",
];
const stageDescriptions = [
  "Create the project and provide source evidence.",
  "Resolve high-impact ambiguity before backlog generation.",
  "Generate requirements and decompose them into executable work.",
  "Enrich, estimate, and inspect the generated hierarchy.",
  "Import verified capacity and prepare assignment and sprint recommendations.",
  "Review board quality before recording a named human decision.",
  "Download the approved six-sheet delivery workbook.",
];
const WORKFLOW_STORAGE_KEY = "sprint-sarthi.workflow.v1";

type WorkflowSnapshot = {
  selectedStage: number;
  project: Project | null;
  document: Document | null;
  analysisJob: AnalysisJob | null;
  session: AnalysisSession | null;
  llmUsage: LLMUsage | null;
  clarification: Clarification | null;
  clarificationsComplete: boolean;
  requirements: Requirement[];
  decompositions: Decomposition[];
  backlog: Backlog | null;
  enriched: boolean;
  estimated: boolean;
  dependencies: BacklogDependency[] | null;
  planningReady: boolean;
  planningIssues: PlanningIssue[];
  assignments: Assignment[];
  sprintPlan: SprintDecision[];
  duplicateCandidates: DuplicateCandidate[];
  qualityResults: QualityResult[];
  boardHealth: BoardHealth | null;
  reviewer: string;
  reviewNote: string;
  publishedExport: PublishedExport | null;
  selectedOption: string;
  customAnswer: string;
  name: string;
  description: string;
};

function readWorkflowSnapshot(): Partial<WorkflowSnapshot> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(
      window.localStorage.getItem(WORKFLOW_STORAGE_KEY) ?? "{}",
    ) as Partial<WorkflowSnapshot>;
  } catch {
    window.localStorage.removeItem(WORKFLOW_STORAGE_KEY);
    return {};
  }
}

const subscribeToHydration = () => () => {};

export default function Home() {
  const [initialSnapshot] = useState(readWorkflowSnapshot);
  const hydrated = useSyncExternalStore(subscribeToHydration, () => true, () => false);
  const [selectedStage, setSelectedStage] = useState(initialSnapshot.selectedStage ?? -1);
  const [project, setProject] = useState<Project | null>(initialSnapshot.project ?? null);
  const [document, setDocument] = useState<Document | null>(initialSnapshot.document ?? null);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(initialSnapshot.analysisJob ?? null);
  const [session, setSession] = useState<AnalysisSession | null>(initialSnapshot.session ?? null);
  const [llmUsage, setLlmUsage] = useState<LLMUsage | null>(initialSnapshot.llmUsage ?? null);
  const [clarification, setClarification] = useState<Clarification | null>(
    initialSnapshot.clarification ?? null,
  );
  const [clarificationsComplete, setClarificationsComplete] = useState(initialSnapshot.clarificationsComplete ?? false);
  const [requirements, setRequirements] = useState<Requirement[]>(initialSnapshot.requirements ?? []);
  const [decompositions, setDecompositions] = useState<Decomposition[]>(initialSnapshot.decompositions ?? []);
  const [backlog, setBacklog] = useState<Backlog | null>(initialSnapshot.backlog ?? null);
  const [enriched, setEnriched] = useState(initialSnapshot.enriched ?? false);
  const [estimated, setEstimated] = useState(initialSnapshot.estimated ?? false);
  const [dependencies, setDependencies] = useState<BacklogDependency[] | null>(initialSnapshot.dependencies ?? null);
  const [planningReady, setPlanningReady] = useState(initialSnapshot.planningReady ?? false);
  const [planningIssues, setPlanningIssues] = useState<PlanningIssue[]>(initialSnapshot.planningIssues ?? []);
  const [assignments, setAssignments] = useState<Assignment[]>(initialSnapshot.assignments ?? []);
  const [sprintPlan, setSprintPlan] = useState<SprintDecision[]>(initialSnapshot.sprintPlan ?? []);
  const [duplicateCandidates, setDuplicateCandidates] = useState<DuplicateCandidate[]>(initialSnapshot.duplicateCandidates ?? []);
  const [qualityResults, setQualityResults] = useState<QualityResult[]>(initialSnapshot.qualityResults ?? []);
  const [boardHealth, setBoardHealth] = useState<BoardHealth | null>(initialSnapshot.boardHealth ?? null);
  const [reviewer, setReviewer] = useState(initialSnapshot.reviewer ?? "");
  const [reviewNote, setReviewNote] = useState(initialSnapshot.reviewNote ?? "");
  const [publishedExport, setPublishedExport] = useState<PublishedExport | null>(initialSnapshot.publishedExport ?? null);
  const [selectedOption, setSelectedOption] = useState(initialSnapshot.selectedOption ?? "");
  const [customAnswer, setCustomAnswer] = useState(initialSnapshot.customAnswer ?? "");
  const [name, setName] = useState(initialSnapshot.name ?? "");
  const [description, setDescription] = useState(initialSnapshot.description ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const unlockedStage = publishedExport
    ? 6
    : boardHealth
      ? 5
      : planningReady || assignments.length > 0 || sprintPlan.length > 0
        ? 4
        : backlog
          ? 3
          : clarificationsComplete || requirements.length > 0 || decompositions.length > 0
            ? 2
            : session
              ? 1
              : 0;
  const visibleStage = selectedStage < 0
    ? unlockedStage
    : Math.min(selectedStage, unlockedStage);

  useEffect(() => {
    if (!hydrated) return;
    const snapshot: WorkflowSnapshot = {
      selectedStage: visibleStage,
      project, document, analysisJob, session, llmUsage, clarification,
      clarificationsComplete, requirements, decompositions, backlog, enriched,
      estimated, dependencies, planningReady, planningIssues, assignments,
      sprintPlan, duplicateCandidates, qualityResults, boardHealth, reviewer,
      reviewNote, publishedExport, selectedOption, customAnswer, name, description,
    };
    try {
      window.localStorage.setItem(WORKFLOW_STORAGE_KEY, JSON.stringify(snapshot));
    } catch {
      window.localStorage.removeItem(WORKFLOW_STORAGE_KEY);
    }
  }, [
    hydrated, visibleStage, project, document, analysisJob, session, llmUsage,
    clarification, clarificationsComplete, requirements, decompositions, backlog,
    enriched, estimated, dependencies, planningReady, planningIssues, assignments,
    sprintPlan, duplicateCandidates, qualityResults, boardHealth, reviewer,
    reviewNote, publishedExport, selectedOption, customAnswer, name, description,
  ]);

  function navigateToStage(index: number) {
    if (index > unlockedStage) return;
    setSelectedStage(index);
    window.requestAnimationFrame(() => {
      const target = window.document.getElementById(`workflow-content-${index}`)
        ?? window.document.getElementById(`workflow-stage-${index}`);
      target?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }

  async function createProject(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description }),
      });
      if (!response.ok) throw new Error("Could not create the project.");
      setProject(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function uploadDocument(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !project) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await fetch(
        `${API_URL}/projects/${project.id}/documents`,
        { method: "POST", body: form },
      );
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Could not upload the document.");
      }
      setDocument(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function beginAnalysis() {
    if (!document) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${API_URL}/documents/${document.id}/process`,
        { method: "POST" },
      );
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Document analysis failed.");
      }
      setAnalysisJob(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function loadNextClarification(sessionId: string) {
    const response = await fetch(
      `${API_URL}/sessions/${sessionId}/clarifications/next`,
    );
    if (!response.ok) throw new Error("Could not load the next clarification.");
    setClarification(await response.json());
    setSelectedOption("");
    setCustomAnswer("");
  }

  async function loadLlmUsage(sessionId: string) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}/usage`);
    if (response.ok) setLlmUsage(await response.json());
  }

  async function startClarification() {
    if (!project) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${API_URL}/projects/${project.id}/sessions`,
        { method: "POST" },
      );
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Could not start clarification.");
      }
      const created: AnalysisSession = await response.json();
      setSession(created);
      setSelectedStage(1);
      await loadNextClarification(created.id);
      await loadLlmUsage(created.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function answerClarification(
    action: "selected" | "default" | "custom" | "skip" | "unknown",
  ) {
    if (!clarification || !session) return;
    if (action === "selected" && !selectedOption) {
      setError("Select an option first.");
      return;
    }
    if (action === "custom" && !customAnswer.trim()) {
      setError("Enter a custom answer first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${API_URL}/clarifications/${clarification.id}/answer`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action,
            option_id: action === "selected" ? selectedOption : null,
            custom_answer: action === "custom" ? customAnswer : null,
          }),
        },
      );
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Could not save the answer.");
      }
      const result: { has_next: boolean; session_status: string } =
        await response.json();
      if (result.has_next) await loadNextClarification(session.id);
      else {
        setClarification(null);
        setClarificationsComplete(true);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function generateRequirements() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${API_URL}/sessions/${session.id}/generate`,
        { method: "POST" },
      );
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Requirement generation failed.");
      }
      const result: { requirements: Requirement[] } = await response.json();
      setRequirements(result.requirements);
      setSelectedStage(2);
      await loadLlmUsage(session.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function runDecomposition() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${API_URL}/sessions/${session.id}/decompose`,
        { method: "POST" },
      );
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Requirement decomposition failed.");
      }
      const result: { decompositions: Decomposition[] } = await response.json();
      setDecompositions(result.decompositions);
      await loadLlmUsage(session.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function runBacklog() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/backlog`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Backlog generation failed.");
      }
      setBacklog(await response.json());
      setSelectedStage(3);
      await loadLlmUsage(session.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function runEnrichment() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/enrich`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Backlog enrichment failed.");
      }
      setBacklog(await response.json());
      setEnriched(true);
      await loadLlmUsage(session.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function runEstimation() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/estimate`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Backlog estimation failed.");
      }
      setBacklog(await response.json());
      setEstimated(true);
      await loadLlmUsage(session.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function runDependencies() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/dependencies`, {
        method: "POST",
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Dependency analysis failed.");
      }
      const result: { dependencies: BacklogDependency[] } = await response.json();
      setDependencies(result.dependencies);
      await loadLlmUsage(session.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function uploadPlanningData(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!session || !file) return;
    setBusy(true);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/planning-data`, {
        method: "POST",
        body,
      });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail ?? "Planning data import failed.");
      }
      const result: { requires_clarification: boolean; issues: PlanningIssue[] } = await response.json();
      setPlanningIssues(result.issues);
      setPlanningReady(!result.requires_clarification);
      if (!result.requires_clarification) {
        setSelectedStage(4);
        await continuePlanningWorkflow(session.id);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function runAssignment() {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      await continuePlanningWorkflow(session.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function postAgent<T>(sessionId: string, path: string): Promise<T> {
    const response = await fetch(`${API_URL}/sessions/${sessionId}/${path}`, { method: "POST" });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.detail ?? `${path} failed.`);
    }
    return response.json();
  }

  async function continuePlanningWorkflow(sessionId: string) {
    const assignmentResult = await postAgent<{ assignments: Assignment[] }>(sessionId, "assign");
    setAssignments(assignmentResult.assignments);
    const sprintResult = await postAgent<{ decisions: SprintDecision[] }>(sessionId, "plan-sprints");
    setSprintPlan(sprintResult.decisions);
    const duplicateResult = await postAgent<{ candidates: DuplicateCandidate[] }>(sessionId, "duplicates");
    setDuplicateCandidates(duplicateResult.candidates);
    const qualityResult = await postAgent<{ results: QualityResult[] }>(sessionId, "quality");
    setQualityResults(qualityResult.results);
    const healthResult = await postAgent<{ health: BoardHealth }>(sessionId, "board-health");
    setBoardHealth(healthResult.health);
    setSelectedStage(5);
    await loadLlmUsage(sessionId);
  }

  async function submitApproval(decision: "approve" | "reject" | "request_changes") {
    if (!session || !reviewer.trim()) {
      setError("Enter the reviewer name before recording a decision.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/approval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, approved_by: reviewer.trim(), note: reviewNote.trim() }),
      });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail ?? "Could not record review decision.");
      }
      if (decision === "approve") {
        const publishResponse = await fetch(`${API_URL}/sessions/${session.id}/publish`, { method: "POST" });
        if (!publishResponse.ok) {
          const result = await publishResponse.json();
          throw new Error(result.detail ?? "Workbook publication failed.");
        }
        setPublishedExport(await publishResponse.json());
        setSelectedStage(6);
      } else {
        setBoardHealth(null);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  if (!hydrated) {
    return <div className="min-h-screen bg-[var(--canvas)]" aria-label="Loading Sprint Sarthi" />;
  }

  return (
    <div className="min-h-screen bg-[var(--canvas)] text-[var(--ink)]">
      <header className="border-b border-[var(--line)] bg-white">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-5 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center bg-[var(--accent)] text-white">
              <Bot size={20} />
            </span>
            <div>
              <strong className="font-display text-lg">Sprint Sarthi</strong>
              <p className="text-xs text-[var(--muted)]">AI Scrum Master</p>
            </div>
          </div>
          <span className="flex items-center gap-2 text-xs font-semibold text-[var(--success)]">
            <ShieldCheck size={16} /> Human-governed
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-[1440px] px-5 py-8 lg:px-8">
        <section className="mb-8 flex flex-col justify-between gap-5 border-b border-[var(--line)] pb-8 md:flex-row md:items-end">
          <div>
            <p className="mb-2 text-xs font-bold uppercase text-[var(--accent)]">
              Backlog workspace
            </p>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">
              Turn architecture into executable work.
            </h1>
            <p className="mt-3 max-w-2xl text-[var(--muted)]">
              Upload source documents, resolve ambiguity, and retain
              traceability from requirement to sprint.
            </p>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="size-2 bg-[var(--success)]" /> SQLite authoritative
          </div>
        </section>
        <nav
          aria-label="Workflow progress"
          className="mb-8 overflow-x-auto border-y border-[var(--line)] bg-white px-4"
        >
          <ol className="grid min-w-[760px] grid-cols-7 items-start py-4">
            {stages.map((stage, index) => (
              <li
                key={stage}
                className={`relative flex flex-col items-center text-xs font-bold ${index <= unlockedStage ? "text-[var(--accent)]" : "text-[var(--muted)]"}`}
              >
                {index > 0 && (
                  <span
                    aria-hidden="true"
                    className={`absolute right-1/2 top-3 h-px w-full ${index <= unlockedStage ? "bg-[var(--accent)]" : "bg-[var(--line-strong)]"}`}
                  />
                )}
                <button
                  type="button"
                  onClick={() => navigateToStage(index)}
                  disabled={index > unlockedStage}
                  aria-current={index === visibleStage ? "step" : undefined}
                  aria-label={`${stage}${index > unlockedStage ? " (locked)" : ""}`}
                  className={`relative z-10 grid size-7 place-items-center border disabled:cursor-not-allowed ${index === visibleStage ? "border-[var(--ink)] bg-[var(--ink)] text-white" : index <= unlockedStage ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-[var(--line-strong)] bg-white"}`}
                >
                  {index < unlockedStage ? <CheckCircle2 size={14} /> : index + 1}
                </button>
                <button
                  type="button"
                  onClick={() => navigateToStage(index)}
                  disabled={index > unlockedStage}
                  className={`mt-2 disabled:cursor-not-allowed ${index === visibleStage ? "underline decoration-2 underline-offset-4" : ""}`}
                >
                  {stage}
                </button>
              </li>
            ))}
          </ol>
        </nav>
        <div className="grid gap-7 lg:grid-cols-[minmax(0,1fr)_360px]">
          <section id={`workflow-stage-${visibleStage}`} className="scroll-mt-6 border border-[var(--line)] bg-white p-5 sm:p-7">
            <div className="mb-6 flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center bg-[var(--soft)] text-[var(--accent)]">
                <Plus size={20} />
              </span>
              <div>
                <h2 className="font-display text-xl font-semibold">
                  {stageHeadings[visibleStage]}
                </h2>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  {stageDescriptions[visibleStage]}
                </p>
              </div>
            </div>
            {visibleStage === 0 && session ? (
              <div className="grid gap-4 border border-[var(--line)] bg-[var(--soft)] p-5">
                <span className="text-xs font-bold uppercase text-[var(--accent)]">Intake complete</span>
                <div>
                  <h3 className="font-display text-xl font-semibold">{project?.name}</h3>
                  <p className="mt-2 text-sm text-[var(--muted)]">
                    {document?.original_name} · {document ? `${(document.size_bytes / 1024).toFixed(1)} KB` : "No document"}
                  </p>
                </div>
                <button type="button" onClick={() => navigateToStage(1)} className="flex h-10 w-fit items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white">
                  Continue to clarification <ArrowRight size={16} />
                </button>
              </div>
            ) : visibleStage === 1 && clarificationsComplete && !clarification ? (
              <div className="flex min-h-64 items-center justify-center border border-[var(--line)] bg-[var(--soft)] p-8 text-center">
                <div>
                  <CheckCircle2 className="mx-auto mb-4 text-[var(--success)]" size={34} />
                  <strong className="block text-lg">Clarifications complete</strong>
                  <p className="mt-2 text-sm text-[var(--muted)]">Answers are retained and available to requirement generation.</p>
                  <button type="button" onClick={() => navigateToStage(2)} className="mx-auto mt-6 flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white">
                    Open generated work <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            ) : !project ? (
              <form onSubmit={createProject} className="grid gap-5">
                <label className="grid gap-2 text-sm font-semibold">
                  Project name
                  <input
                    required
                    minLength={2}
                    maxLength={200}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Payments modernization"
                    className="h-11 border border-[var(--line-strong)] px-3 font-normal outline-none focus:border-[var(--accent)]"
                  />
                </label>
                <label className="grid gap-2 text-sm font-semibold">
                  Objective
                  <textarea
                    maxLength={5000}
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="What should the team deliver?"
                    className="min-h-28 resize-y border border-[var(--line-strong)] p-3 font-normal outline-none focus:border-[var(--accent)]"
                  />
                </label>
                <button
                  disabled={busy}
                  className="flex h-11 w-fit items-center gap-2 bg-[var(--ink)] px-5 text-sm font-bold text-white disabled:opacity-50"
                >
                  {busy ? (
                    <Loader2 className="animate-spin" size={17} />
                  ) : (
                    <Plus size={17} />
                  )}{" "}
                  Create project
                </button>
              </form>
            ) : !document ? (
              <label className="grid min-h-64 cursor-pointer place-items-center border border-dashed border-[var(--line-strong)] bg-[var(--soft)] p-8 text-center focus-within:border-[var(--accent)]">
                <input
                  className="sr-only"
                  type="file"
                  accept=".pdf,.docx,.xlsx,.txt,.md,.csv"
                  onChange={uploadDocument}
                  disabled={busy}
                />
                <span>
                  <Upload
                    className="mx-auto mb-4 text-[var(--accent)]"
                    size={30}
                  />
                  <strong className="block">
                    {busy
                      ? "Uploading securely..."
                      : "Choose a source document"}
                  </strong>
                  <small className="mt-2 block text-[var(--muted)]">
                    PDF, DOCX, XLSX, TXT, Markdown, or CSV. Stored locally with
                    a SHA-256 fingerprint.
                  </small>
                </span>
              </label>
            ) : clarification ? (
              <div className="border border-[var(--line)] bg-[var(--soft)] p-5 sm:p-6">
                <div className="mb-5 flex items-start justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase">
                      <span className="text-[var(--accent)]">
                        {clarification.requirement_id}
                      </span>
                      <span className={clarification.severity === "critical" ? "bg-red-100 px-2 py-1 text-red-800" : clarification.severity === "high" ? "bg-amber-100 px-2 py-1 text-amber-900" : "bg-white px-2 py-1 text-[var(--muted)]"}>
                        {clarification.severity}
                      </span>
                      <span className="text-[var(--muted)]">
                        {clarification.blocking ? "Blocking" : "Non-blocking"}
                      </span>
                    </div>
                    <h3 className="mt-2 font-display text-xl font-semibold">
                      {clarification.question}
                    </h3>
                    <p className="mt-2 text-sm text-[var(--muted)]">
                      {clarification.reason}
                    </p>
                    <p className="mt-2 text-xs text-[var(--muted)]">
                      Missing field: {clarification.missing_field.replaceAll("_", " ")}
                    </p>
                  </div>
                  <Bot className="shrink-0 text-[var(--accent)]" size={24} />
                </div>
                <fieldset className="grid gap-2">
                  <legend className="sr-only">Answer options</legend>
                  {clarification.options.map((option) => (
                    <label
                      key={option.id}
                      className={`flex cursor-pointer items-center gap-3 border p-3 text-sm ${selectedOption === option.id ? "border-[var(--accent)] bg-white" : "border-[var(--line)]"}`}
                    >
                      <input
                        type="radio"
                        name="clarification-option"
                        value={option.id}
                        checked={selectedOption === option.id}
                        onChange={() => setSelectedOption(option.id)}
                      />
                      <span>{option.label}</span>
                      {option.id === clarification.recommended_option_id && (
                        <small className="ml-auto font-bold text-[var(--success)]">
                          Recommended
                        </small>
                      )}
                    </label>
                  ))}
                </fieldset>
                {clarification.allow_custom_answer && (
                  <textarea
                    value={customAnswer}
                    onChange={(event) => setCustomAnswer(event.target.value)}
                    placeholder="Or provide a custom answer"
                    className="mt-4 min-h-20 w-full border border-[var(--line-strong)] bg-white p-3 text-sm outline-none focus:border-[var(--accent)]"
                  />
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy || !selectedOption}
                    onClick={() => answerClarification("selected")}
                    className="h-10 bg-[var(--ink)] px-4 text-sm font-bold text-white disabled:opacity-40"
                  >
                    Submit selected
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => answerClarification("default")}
                    className="h-10 border border-[var(--line-strong)] bg-white px-4 text-sm font-bold"
                  >
                    Use default
                  </button>
                  {clarification.allow_custom_answer && (
                    <button
                      type="button"
                      disabled={busy || !customAnswer.trim()}
                      onClick={() => answerClarification("custom")}
                      className="h-10 border border-[var(--line-strong)] bg-white px-4 text-sm font-bold disabled:opacity-40"
                    >
                      Use custom answer
                    </button>
                  )}
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => answerClarification("unknown")}
                    className="h-10 border border-[var(--line-strong)] bg-white px-4 text-sm font-bold"
                  >
                    Mark unknown
                  </button>
                  {!clarification.blocking && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => answerClarification("skip")}
                      className="h-10 px-4 text-sm font-bold text-[var(--muted)]"
                    >
                      Skip
                    </button>
                  )}
                </div>
                <p className="mt-5 text-xs text-[var(--muted)]">
                  Source: {clarification.source_references.join("; ")}
                </p>
              </div>
            ) : requirements.length > 0 ? (
              <div id="workflow-content-2" className="scroll-mt-6 grid gap-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold uppercase text-[var(--accent)]">
                      Requirement agent
                    </span>
                    <h3 className="mt-1 font-display text-xl font-semibold">
                      Normalized requirements
                    </h3>
                  </div>
                  {decompositions.length > 0 ? (
                    <span className="text-sm font-bold text-[var(--success)]">
                      {decompositions.length} components
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={runDecomposition}
                      disabled={busy}
                      className="flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50"
                    >
                      {busy ? <Loader2 className="animate-spin" size={16} /> : <GitBranch size={16} />}
                      {busy ? "Decomposing..." : "Run decomposition"}
                    </button>
                  )}
                </div>
                {requirements.map((requirement) => {
                  const actors = requirement.actors ?? [];
                  const systems = requirement.systems ?? [];
                  const clarificationReasons =
                    requirement.clarification_reasons ?? [];
                  return (
                    <article
                      key={requirement.id}
                      className="border border-[var(--line)] bg-[var(--soft)] p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <strong className="text-sm text-[var(--accent)]">
                            {requirement.stable_id}
                          </strong>
                          <span className="bg-white px-2 py-1 text-xs font-semibold capitalize">
                            {requirement.category.replace("_", " ")}
                          </span>
                          <span className="bg-white px-2 py-1 text-xs font-semibold capitalize">
                            {requirement.requirement_status ?? "candidate"}
                          </span>
                          <span className="bg-white px-2 py-1 text-xs font-semibold">
                            {requirement.priority}
                          </span>
                          <span className="bg-white px-2 py-1 text-xs font-semibold">
                            {Math.round((requirement.confidence ?? 0) * 100)}%
                            confidence
                          </span>
                          {requirement.requires_clarification && (
                            <span className="bg-amber-100 px-2 py-1 text-xs font-bold text-amber-900">
                              Review required
                            </span>
                          )}
                        </div>
                        <Traceability
                          apiUrl={API_URL}
                          itemId={requirement.id}
                          itemType="requirement"
                          itemLabel={`${requirement.stable_id}: ${requirement.title}`}
                          sourceCount={requirement.source_references.length}
                        />
                      </div>
                      <h4 className="mt-3 font-display text-lg font-semibold">
                        {requirement.title}
                      </h4>
                      <p className="mt-2 text-sm text-[var(--muted)]">
                        {requirement.description}
                      </p>
                      {(actors.length > 0 || systems.length > 0) && (
                        <p className="mt-3 text-xs text-[var(--muted)]">
                          {actors.length > 0 && `Actors: ${actors.join(", ")}`}
                          {actors.length > 0 && systems.length > 0 && " · "}
                          {systems.length > 0 &&
                            `Systems: ${systems.join(", ")}`}
                        </p>
                      )}
                      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                        {requirement.acceptance_criteria.map((criterion) => (
                          <li key={criterion}>{criterion}</li>
                        ))}
                      </ul>
                      {clarificationReasons.length > 0 && (
                        <div className="mt-3 border-l-2 border-amber-500 pl-3 text-sm text-amber-900">
                          {clarificationReasons.join(" ")}
                        </div>
                      )}
                    </article>
                  );
                })}
                {decompositions.length > 0 && (
                  <section id="workflow-content-3" className="scroll-mt-6 mt-4 border-t border-[var(--line)] pt-5">
                    <div className="mb-4 flex items-center justify-between gap-4">
                      <div>
                        <span className="text-xs font-bold uppercase text-[var(--accent)]">Decomposition agent</span>
                        <h3 className="mt-1 font-display text-xl font-semibold">Delivery components</h3>
                      </div>
                      {backlog ? (
                        <span className="text-sm font-bold text-[var(--success)]">
                          {backlog.epics.length + backlog.stories.length + backlog.tasks.length} backlog items
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={runBacklog}
                          disabled={busy}
                          className="flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50"
                        >
                          {busy ? <Loader2 className="animate-spin" size={16} /> : <GitBranch size={16} />}
                          {busy ? "Building..." : "Build backlog"}
                        </button>
                      )}
                    </div>
                    <div className="grid gap-3">
                      {decompositions.map((item) => (
                        <article key={item.id} className="border border-[var(--line)] bg-white p-4">
                          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                            <strong className="text-[var(--accent)]">{item.stable_id}</strong>
                            <span className="bg-[var(--soft)] px-2 py-1 capitalize">{item.component_type.replaceAll("_", " ")}</span>
                            <span className="bg-[var(--soft)] px-2 py-1 capitalize">{item.suggested_backlog_level}</span>
                            <span className="bg-amber-100 px-2 py-1 text-amber-900">Review inferred</span>
                          </div>
                          <h4 className="mt-3 font-display text-lg font-semibold">{item.title}</h4>
                          <p className="mt-1 text-sm text-[var(--muted)]">{item.description}</p>
                          <p className="mt-3 text-xs text-[var(--muted)]">From {item.requirement_ids.join(", ")} · {Math.round(item.confidence * 100)}% confidence · {item.source_references.length} sources</p>
                        </article>
                      ))}
                    </div>
                  </section>
                )}
                {backlog && (
                  <section className="mt-4 border-t border-[var(--line)] pt-5">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <span className="text-xs font-bold uppercase text-[var(--accent)]">Backlog agent</span>
                        <h3 className="mt-1 font-display text-xl font-semibold">Epic, story, and task hierarchy</h3>
                      </div>
                      {dependencies !== null ? (
                        <span className="text-sm font-bold text-[var(--success)]">Dependencies analyzed</span>
                      ) : estimated ? (
                        <button type="button" onClick={runDependencies} disabled={busy} className="flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50">
                          {busy ? <Loader2 className="animate-spin" size={16} /> : <GitBranch size={16} />}
                          {busy ? "Analyzing..." : "Analyze dependencies"}
                        </button>
                      ) : enriched ? (
                        <button type="button" onClick={runEstimation} disabled={busy} className="flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50">
                          {busy ? <Loader2 className="animate-spin" size={16} /> : <Bot size={16} />}
                          {busy ? "Estimating..." : "Estimate backlog"}
                        </button>
                      ) : (
                        <button type="button" onClick={runEnrichment} disabled={busy} className="flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50">
                          {busy ? <Loader2 className="animate-spin" size={16} /> : <Bot size={16} />}
                          {busy ? "Enriching..." : "Enrich backlog"}
                        </button>
                      )}
                    </div>
                    <div className="mt-4 grid gap-4">
                      {backlog.epics.map((epic) => (
                        <article key={epic.id} className="border-l-4 border-[var(--accent)] bg-white p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <strong className="text-xs text-[var(--accent)]">{epic.stable_id} · EPIC</strong>
                              <h4 className="mt-1 font-display text-lg font-semibold">{epic.title}</h4>
                              <p className="mt-1 text-sm text-[var(--muted)]">{epic.business_value}</p>
                              <span className="mt-2 inline-block bg-[var(--soft)] px-2 py-1 text-xs font-semibold">{epic.priority}</span>
                            </div>
                            <Traceability apiUrl={API_URL} itemId={epic.id} itemType="epic" itemLabel={`${epic.stable_id}: ${epic.title}`} sourceCount={epic.source_references.length} />
                          </div>
                          <div className="mt-4 grid gap-3 pl-3">
                            {backlog.stories.filter((story) => story.epic_stable_id === epic.stable_id).map((story) => (
                              <div key={story.id} className="border-l-2 border-[var(--line)] bg-[var(--soft)] p-3">
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <strong className="text-xs text-[var(--accent)]">{story.stable_id} · STORY</strong>
                                    <h5 className="mt-1 font-semibold">{story.title}</h5>
                                    <p className="mt-1 text-sm text-[var(--muted)]">{story.user_story}</p>
                                    {story.story_points !== null && (
                                      <p className="mt-2 text-xs font-semibold">{story.story_points} points · {story.estimation_rationale}</p>
                                    )}
                                    {story.acceptance_criteria.length > 0 && (
                                      <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-[var(--muted)]">
                                        {story.acceptance_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}
                                      </ul>
                                    )}
                                  </div>
                                  <Traceability apiUrl={API_URL} itemId={story.id} itemType="story" itemLabel={`${story.stable_id}: ${story.title}`} sourceCount={story.source_references.length} />
                                </div>
                                <div className="mt-3 grid gap-2 pl-3">
                                  {backlog.tasks.filter((task) => task.story_stable_id === story.stable_id).map((task) => (
                                    <div key={task.id} className="flex items-start justify-between gap-3 border-l border-[var(--line)] bg-white p-3">
                                      <div>
                                        <strong className="text-xs text-[var(--accent)]">{task.stable_id} · {task.task_type.toUpperCase()}</strong>
                                        <p className="mt-1 text-sm font-semibold">{task.title}</p>
                                        {task.estimated_hours !== null && (
                                          <p className="mt-1 text-xs text-[var(--muted)]">{task.estimated_hours} hours · {task.estimation_rationale}</p>
                                        )}
                                      </div>
                                      <Traceability apiUrl={API_URL} itemId={task.id} itemType="task" itemLabel={`${task.stable_id}: ${task.title}`} sourceCount={task.source_references.length} />
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </article>
                      ))}
                    </div>
                    {dependencies !== null && (
                      <div className="mt-4 border border-[var(--line)] bg-[var(--soft)] p-4">
                        <strong className="text-sm">Dependency analysis</strong>
                        {dependencies.length === 0 ? (
                          <p className="mt-2 text-sm text-[var(--muted)]">No evidence-supported dependencies were identified.</p>
                        ) : (
                          <div className="mt-3 grid gap-2">
                            {dependencies.map((dependency) => (
                              <div key={dependency.id} className="bg-white p-3 text-sm">
                                <strong>{dependency.source_stable_id} {dependency.dependency_type.replaceAll("_", " ")} {dependency.target_stable_id}</strong>
                                <p className="mt-1 text-[var(--muted)]">{dependency.explanation} · {dependency.risk} risk</p>
                              </div>
                            ))}
                          </div>
                        )}
                        <div id="workflow-content-4" className="scroll-mt-6 mt-4 border-t border-[var(--line)] pt-4">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <strong className="text-sm">Planning data</strong>
                              <p className="mt-1 text-xs text-[var(--muted)]">Upload the Teams, TeamMembers, Sprints, Holidays, and optional Leaves workbook.</p>
                            </div>
                            {planningReady ? (
                              assignments.length > 0 ? (
                                <span className="text-sm font-bold text-[var(--success)]">Assignments proposed</span>
                              ) : (
                                <button type="button" onClick={runAssignment} disabled={busy} className="flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50">
                                  {busy ? <Loader2 className="animate-spin" size={16} /> : <Bot size={16} />}
                                  {busy ? "Matching..." : "Recommend assignments"}
                                </button>
                              )
                            ) : (
                              <label className="flex h-10 cursor-pointer items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white">
                                <Upload size={16} /> {busy ? "Validating..." : "Upload planning XLSX"}
                                <input type="file" accept=".xlsx" onChange={uploadPlanningData} disabled={busy} className="sr-only" />
                              </label>
                            )}
                          </div>
                          {planningIssues.length > 0 && (
                            <div className="mt-3 grid gap-2">
                              {planningIssues.map((issue, index) => (
                                <p key={`${issue.sheet}-${issue.row}-${issue.field}-${index}`} className={`border-l-2 px-3 py-2 text-xs ${issue.blocking ? "border-red-500 bg-red-50 text-red-900" : "border-amber-500 bg-amber-50 text-amber-900"}`}>
                                  {issue.sheet}{issue.row ? ` row ${issue.row}` : ""}: {issue.message}
                                </p>
                              ))}
                            </div>
                          )}
                          {assignments.length > 0 && (
                            <div className="mt-4 grid gap-2">
                              {assignments.map((assignment) => (
                                <div key={assignment.id} className="bg-white p-3 text-sm">
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <strong>{assignment.item_stable_id} → {assignment.team_member_name}</strong>
                                    <span className="bg-amber-100 px-2 py-1 text-xs font-bold text-amber-900">Proposed · review required</span>
                                  </div>
                                  <p className="mt-1 text-[var(--muted)]">{assignment.role}{assignment.department ? ` · ${assignment.department}` : ""}{assignment.recommended_hours ? ` · ${assignment.recommended_hours} hours` : ""}</p>
                                  <p className="mt-2 text-xs text-[var(--muted)]">{assignment.reason} · {Math.round(assignment.match_score * 100)}% skill match</p>
                                </div>
                              ))}
                            </div>
                          )}
                          {sprintPlan.length > 0 && (
                            <div id="workflow-content-5" className="scroll-mt-6 mt-4 border-t border-[var(--line)] pt-4">
                              <strong className="text-sm">Proposed sprint plan</strong>
                              <div className="mt-2 grid gap-2">
                                {sprintPlan.map((decision) => (
                                  <div key={decision.id} className="bg-white p-3 text-sm">
                                    <strong>{decision.story_stable_id} · {decision.decision === "planned" ? decision.sprint_name : "Deferred"}</strong>
                                    <p className="mt-1 text-[var(--muted)]">{decision.story_points} points{decision.assignee_name ? ` · ${decision.assignee_name}` : ""} · {decision.reason}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {qualityResults.length > 0 && boardHealth && (
                            <div className="mt-4 border-t border-[var(--line)] pt-4">
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <div>
                                  <strong className="text-sm">Board health: {boardHealth.score}/100 · {boardHealth.risk_level} risk</strong>
                                  <p className="mt-1 text-xs text-[var(--muted)]">{qualityResults.filter((item) => item.passed).length}/{qualityResults.length} items pass quality · {duplicateCandidates.length} duplicate candidates</p>
                                </div>
                                <span className="bg-amber-100 px-2 py-1 text-xs font-bold text-amber-900">Human approval required</span>
                              </div>
                              {boardHealth.issues.map((issue) => <p key={issue} className="mt-2 text-xs text-amber-900">{issue}</p>)}
                              {!publishedExport && (
                                <div className="mt-4 grid gap-3 md:grid-cols-2">
                                  <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="Reviewer name" className="h-10 border border-[var(--line)] bg-white px-3 text-sm" />
                                  <input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} placeholder="Review note" className="h-10 border border-[var(--line)] bg-white px-3 text-sm" />
                                  <div className="flex flex-wrap gap-2 md:col-span-2">
                                    <button type="button" onClick={() => submitApproval("approve")} disabled={busy || !reviewer.trim()} className="h-10 bg-[var(--success)] px-4 text-sm font-bold text-white disabled:opacity-50">Approve & publish</button>
                                    <button type="button" onClick={() => submitApproval("request_changes")} disabled={busy || !reviewer.trim()} className="h-10 border border-[var(--line)] bg-white px-4 text-sm font-bold disabled:opacity-50">Request changes</button>
                                    <button type="button" onClick={() => submitApproval("reject")} disabled={busy || !reviewer.trim()} className="h-10 border border-red-300 bg-red-50 px-4 text-sm font-bold text-red-800 disabled:opacity-50">Reject</button>
                                  </div>
                                </div>
                              )}
                              {publishedExport && (
                                <a id="workflow-content-6" href={`${API_URL.replace(/\/api\/v1$/, "")}${publishedExport.download_url}`} className="scroll-mt-6 mt-4 inline-flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white">
                                  <FileText size={16} /> Download {publishedExport.filename}
                                </a>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </section>
                )}
              </div>
            ) : clarificationsComplete ? (
              <div className="flex min-h-64 items-center justify-center border border-[var(--line)] bg-[var(--soft)] p-8 text-center">
                <div>
                  <CheckCircle2
                    className="mx-auto mb-4 text-[var(--success)]"
                    size={34}
                  />
                  <strong className="block text-lg">
                    Clarifications complete
                  </strong>
                  <p className="mt-2 text-sm text-[var(--muted)]">
                    Approved answers are ready for normalization into atomic
                    requirements.
                  </p>
                  <button
                    type="button"
                    onClick={generateRequirements}
                    disabled={busy}
                    className="mt-6 flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50"
                  >
                    {busy ? (
                      <Loader2 className="animate-spin" size={16} />
                    ) : (
                      <Bot size={16} />
                    )}{" "}
                    {busy
                      ? "Generating requirements..."
                      : "Generate requirements"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex min-h-64 items-center justify-center border border-[var(--line)] bg-[var(--soft)] p-8 text-center">
                <div>
                  <CheckCircle2
                    className="mx-auto mb-4 text-[var(--success)]"
                    size={34}
                  />
                  <strong className="block text-lg">
                    {analysisJob ? "Analysis complete" : "Document secured"}
                  </strong>
                  <p className="mt-2 text-sm text-[var(--muted)]">
                    {analysisJob
                      ? "Source content was extracted and stored for clarification."
                      : `${document.original_name} · ${(document.size_bytes / 1024).toFixed(1)} KB`}
                  </p>
                  {!analysisJob ? (
                    <button
                      type="button"
                      onClick={beginAnalysis}
                      disabled={busy}
                      className="mt-6 flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50"
                    >
                      {busy ? (
                        <Loader2 className="animate-spin" size={16} />
                      ) : (
                        <Bot size={16} />
                      )}{" "}
                      {busy ? "Analyzing..." : "Begin analysis"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={startClarification}
                      disabled={busy}
                      className="mt-6 flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white disabled:opacity-50"
                    >
                      {busy ? (
                        <Loader2 className="animate-spin" size={16} />
                      ) : (
                        <ArrowRight size={16} />
                      )}{" "}
                      {busy ? "Generating questions..." : "Start clarification"}
                    </button>
                  )}
                </div>
              </div>
            )}
            {error && (
              <p
                role="alert"
                className="mt-4 border-l-4 border-red-600 bg-red-50 p-3 text-sm text-red-800"
              >
                {error}
              </p>
            )}
          </section>
          <aside className="border border-[var(--line)] bg-[var(--ink)] p-6 text-white">
            <h2 className="font-display text-lg font-semibold">
              Control plane
            </h2>
            <div className="mt-6 grid gap-5">
              <Status
                icon={<FileText size={17} />}
                label="Source evidence"
                value={
                  analysisJob
                    ? "Extracted"
                    : document
                      ? "1 document"
                      : "Awaiting upload"
                }
              />
              <Status
                icon={<Bot size={17} />}
                label="Clarification"
                value={
                  clarificationsComplete
                    ? "Complete"
                    : clarification
                      ? "In progress"
                      : "Not started"
                }
              />
              <Status
                icon={<FileText size={17} />}
                label="Requirements"
                value={
                  requirements.length
                    ? `${requirements.length} generated`
                    : "Not generated"
                }
              />
              <Status
                icon={<Coins size={17} />}
                label="LLM usage"
                value={
                  llmUsage
                    ? `${llmUsage.total_tokens.toLocaleString()} tokens consumed`
                    : "No usage recorded"
                }
              />
              {llmUsage && (
                <div className="-mt-3 ml-7 border-l border-white/15 pl-3 text-xs leading-5 text-white/60">
                  <p>
                    {llmUsage.input_tokens.toLocaleString()} input ·{" "}
                    {llmUsage.output_tokens.toLocaleString()} output
                  </p>
                  <p>
                    {llmUsage.remaining_reported
                      ? `${llmUsage.remaining_tokens?.toLocaleString()} rate-limit tokens available`
                      : "Rate-limit availability not reported"}
                  </p>
                  {llmUsage.remaining_reported && (
                    <p>
                      Rolling provider window; it may replenish between calls.
                    </p>
                  )}
                </div>
              )}
              <Status
                icon={<GitBranch size={17} />}
                label="Dependency integrity"
                value="Not analyzed"
              />
              <Status
                icon={<ShieldCheck size={17} />}
                label="Publishing gate"
                value="Approval required"
              />
            </div>
            <div className="mt-8 border-t border-white/15 pt-5 text-xs leading-5 text-white/65">
              No API keys are sent to this client. Final exports remain locked
              until a named reviewer approves the project.
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

function Status({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 text-[var(--accent-light)]">{icon}</span>
      <div>
        <p className="text-xs text-white/55">{label}</p>
        <p className="mt-1 text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}
