"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState, useSyncExternalStore } from "react";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Coins,
  Download,
  Eye,
  EyeOff,
  FileText,
  FolderOpen,
  GitBranch,
  Home as HomeIcon,
  LockKeyhole,
  LogIn,
  LogOut,
  Loader2,
  Plus,
  ShieldCheck,
  Trash2,
  Upload,
  UserRound,
  X,
} from "lucide-react";
import { Traceability } from "@/components/Traceability";

type Project = {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at?: string;
  workflow_state?: string;
  current_node?: string | null;
  agent_index?: number;
};
type Document = {
  id: string;
  document_code?: string;
  project_id?: string;
  original_name: string;
  size_bytes: number;
  status: string;
  created_at?: string;
};
type AnalysisJob = {
  id: string;
  status: string;
  progress: number;
  error: string | null;
};
type AnalysisSession = { id: string; thread_id: string; status: string; current_node?: string | null };
type DocumentChunk = {
  id: string;
  chunk_id: string;
  document_id: string;
  file_name: string;
  page_number: number | null;
  section_heading: string;
  content: string;
  token_count: number;
  extraction_confidence: number;
  embedding_status: string;
  embedding_model: string | null;
  embedding_dimensions: number | null;
};
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
type ClarificationHistory = {
  id: string;
  requirement_id: string;
  question: string;
  severity: string;
  status: string;
  action: string | null;
  answer: string | null;
  answered_at: string | null;
};
type AgentMessage = {
  id: string;
  agent_name: string;
  role: "human" | "assistant";
  content: string;
  created_at: string;
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
  architecture_layer: string;
  business_value: string;
  priority: string;
  acceptance_criteria?: string[];
  source_references: string[];
};
type BacklogFeature = {
  id: string;
  stable_id: string;
  epic_stable_id: string;
  title: string;
  description: string;
  business_value: string;
  source_references: string[];
};
type BacklogStory = {
  id: string;
  stable_id: string;
  epic_stable_id: string;
  feature_stable_id: string;
  title: string;
  user_story: string;
  priority: string;
  acceptance_criteria: string[];
  definition_of_done: string[];
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
  work_category: string;
  acceptance_criteria: string[];
  definition_of_done: string[];
  estimated_hours: number | null;
  estimation_rationale: string;
  source_references: string[];
};
type Backlog = {
  epics: BacklogEpic[];
  features: BacklogFeature[];
  stories: BacklogStory[];
  tasks: BacklogTask[];
};
type QualityClarification = {
  id: string;
  item_id: string;
  item_type: "epic" | "feature" | "story" | "task";
  missing_fields: string[];
  question: string;
  status: string;
};
type NewStoryCheck = {
  id: string;
  classification: "duplicate" | "new" | "clarification";
  equivalent_story_id: string | null;
  suggested_feature_id: string | null;
  suggested_sprint_id: string | null;
  rationale: string;
  clarifying_questions: string[];
  confidence: number;
  status: string;
};
type EstimationBrief = {
  id?: string;
  session_id?: string;
  answered_by: string;
  ranked_epic_ids: string[];
  priority_rationale: string;
  created_at?: string;
  updated_at?: string;
};
type EstimationEpicOption = { stable_id: string; title: string; business_value: string; architecture_layer: string; current_priority: string };
type EstimationBriefWorkspace = { brief: EstimationBrief | null; epics: EstimationEpicOption[]; parallel_groups: string[][]; parallelism_note: string };
type BacklogDependency = {
  id: string;
  source_stable_id: string;
  target_stable_id: string;
  dependency_type: string;
  risk: string;
  explanation: string;
  confidence: number;
};

const emptyEstimationBrief: EstimationBrief = {
  answered_by: "",
  ranked_epic_ids: [],
  priority_rationale: "",
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
type SprintScopeTask = {
  stable_id: string;
  story_stable_id: string;
  title: string;
  work_category: string;
  estimated_hours: number | null;
  selected: boolean;
};
type SprintScopeStory = {
  stable_id: string;
  title: string;
  story_points: number;
  priority: string;
  selected: boolean;
  tasks: SprintScopeTask[];
};
type SprintScopeReview = {
  id: string | null;
  reviewed_by: string;
  selected_task_ids: string[];
  discarded_task_ids: string[];
  selected_story_ids: string[];
  note: string;
  reviewed: boolean;
  stories: SprintScopeStory[];
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
type WorkflowResume = {
  project: Project;
  documents: Document[];
  session: AnalysisSession | null;
  agent_index: number;
  clarification: Clarification | null;
  clarifications_complete: boolean;
  requirements: Requirement[];
  decompositions: Decomposition[];
  backlog: Backlog | null;
  enriched: boolean;
  estimated: boolean;
  dependencies: BacklogDependency[] | null;
  planning_ready: boolean;
  assignments: Assignment[];
  sprint_plan: SprintDecision[];
  duplicate_candidates: DuplicateCandidate[];
  duplicates_complete: boolean;
  quality_results: QualityResult[];
  board_health: BoardHealth | null;
  approved: boolean;
  published_export: PublishedExport | null;
};
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
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
const carImages = [
  "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1553440569-bcc63803a83d?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1503736334956-4c8f8e92946d?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1525609004556-c46c7d6cf023?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1544829099-b9a0c07fad1a?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1542362567-b07e54358753?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1580273916550-e323be2ae537?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1619767886558-efdc259cde1a?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1504215680853-026ed2a45def?auto=format&fit=crop&w=640&q=80",
  "https://images.unsplash.com/photo-1597404294360-feeeda04612e?auto=format&fit=crop&w=640&q=80",
];
const agentStages = [
  { label: "Intake", description: "Creating the project workspace and collecting architecture evidence without making unsupported assumptions.", section: 0, target: "workflow-stage-0" },
  { label: "Document Analysis", description: "Extracting structured source content from every uploaded architecture document and retaining its provenance.", section: 0, target: "workflow-analysis" },
  { label: "Clarification", description: "Identifying consequential gaps and waiting for human answers before generation can proceed.", section: 1, target: "workflow-stage-1" },
  { label: "Requirement", description: "Turning verified evidence and human clarifications into traceable functional and non-functional requirements.", section: 2, target: "workflow-agent-page" },
  { label: "Decomposition", description: "Breaking requirements into bounded capabilities and implementation components while preserving evidence links.", section: 2, target: "workflow-agent-page" },
  { label: "Backlog", description: "Building the Epic, Story, and Task hierarchy from supported decomposition items.", section: 3, target: "workflow-agent-page" },
  { label: "Enrichment", description: "Adding priority, business value, and acceptance criteria to the proposed backlog.", section: 3, target: "workflow-agent-page" },
  { label: "Estimation", description: "Estimating story points and task hours with an explicit rationale for every recommendation.", section: 3, target: "workflow-agent-page" },
  { label: "Dependency", description: "Detecting prerequisite relationships and delivery risks across the generated backlog.", section: 3, target: "workflow-agent-page" },
  { label: "Planning Data", description: "Importing verified team, capacity, sprint, holiday, and leave data for responsible planning.", section: 4, target: "workflow-content-4-plan" },
  { label: "Assignment", description: "Recommending owners from verified skills and capacity while keeping decisions proposed.", section: 4, target: "workflow-content-4-plan" },
  { label: "Sprint Planning", description: "Sequencing stories across available sprints using capacity and dependency constraints.", section: 4, target: "workflow-content-4-plan" },
  { label: "Duplicate Detection", description: "Comparing backlog items for overlap and proposing consolidation where evidence supports it.", section: 4, target: "workflow-content-4-plan" },
  { label: "Quality", description: "Running deterministic completeness, traceability, and consistency checks across generated work.", section: 5, target: "workflow-content-5" },
  { label: "Board Health", description: "Summarizing readiness, unresolved risks, and quality signals before human review.", section: 5, target: "workflow-content-5" },
  { label: "Human Approval", description: "Waiting for a named reviewer to approve, reject, or request changes before publication.", section: 5, target: "workflow-content-5" },
  { label: "Publisher", description: "Producing the governed six-sheet workbook only after explicit human approval.", section: 6, target: "workflow-content-6" },
].map((stage, index) => ({ ...stage, image: carImages[index] }));
const WORKFLOW_STORAGE_KEY = "sprint-sarthi.workflow.v1";

type WorkflowSnapshot = {
  authenticated: boolean;
  selectedStage: number;
  selectedAgent: number;
  documents: Document[];
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
  duplicatesComplete: boolean;
  qualityResults: QualityResult[];
  boardHealth: BoardHealth | null;
  approved: boolean;
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
  const [authenticated, setAuthenticated] = useState(initialSnapshot.authenticated ?? false);
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [selectedStage, setSelectedStage] = useState(initialSnapshot.selectedStage ?? -1);
  const [selectedAgent, setSelectedAgent] = useState(initialSnapshot.selectedAgent ?? -1);
  const [transitionDirection, setTransitionDirection] = useState<"forward" | "backward">("forward");
  const [homeOpen, setHomeOpen] = useState(!initialSnapshot.project);
  const [projectHistory, setProjectHistory] = useState<Project[]>([]);
  const [historyProject, setHistoryProject] = useState<Project | null>(null);
  const [deleteProjectArmed, setDeleteProjectArmed] = useState(false);
  const [historyDocuments, setHistoryDocuments] = useState<Document[]>([]);
  const [project, setProject] = useState<Project | null>(initialSnapshot.project ?? null);
  const [document, setDocument] = useState<Document | null>(initialSnapshot.document ?? null);
  const [documents, setDocuments] = useState<Document[]>(initialSnapshot.documents ?? (initialSnapshot.document ? [initialSnapshot.document] : []));
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(initialSnapshot.analysisJob ?? null);
  const [session, setSession] = useState<AnalysisSession | null>(initialSnapshot.session ?? null);
  const [selectedChunkDocument, setSelectedChunkDocument] = useState<Document | null>(null);
  const [documentChunks, setDocumentChunks] = useState<DocumentChunk[]>([]);
  const [clarificationHistory, setClarificationHistory] = useState<ClarificationHistory[]>([]);
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [agentPrompt, setAgentPrompt] = useState("");
  const [agentPromptBusy, setAgentPromptBusy] = useState(false);
  const [llmUsage, setLlmUsage] = useState<LLMUsage | null>(initialSnapshot.llmUsage ?? null);
  const [clarification, setClarification] = useState<Clarification | null>(
    initialSnapshot.clarification ?? null,
  );
  const [clarificationsComplete, setClarificationsComplete] = useState(initialSnapshot.clarificationsComplete ?? false);
  const [requirements, setRequirements] = useState<Requirement[]>(initialSnapshot.requirements ?? []);
  const [decompositions, setDecompositions] = useState<Decomposition[]>(initialSnapshot.decompositions ?? []);
  const [backlog, setBacklog] = useState<Backlog | null>(initialSnapshot.backlog ? { ...initialSnapshot.backlog, features: initialSnapshot.backlog.features ?? [] } : null);
  const [enriched, setEnriched] = useState(initialSnapshot.enriched ?? false);
  const [estimated, setEstimated] = useState(initialSnapshot.estimated ?? false);
  const [estimationBrief, setEstimationBrief] = useState<EstimationBrief | null>(null);
  const [estimationOptions, setEstimationOptions] = useState<Omit<EstimationBriefWorkspace, "brief">>({ epics: [], parallel_groups: [], parallelism_note: "" });
  const [estimationDraft, setEstimationDraft] = useState<EstimationBrief>(emptyEstimationBrief);
  const [estimationBriefBusy, setEstimationBriefBusy] = useState(false);
  const [dependencies, setDependencies] = useState<BacklogDependency[] | null>(initialSnapshot.dependencies ?? null);
  const [planningReady, setPlanningReady] = useState(initialSnapshot.planningReady ?? false);
  const [planningIssues, setPlanningIssues] = useState<PlanningIssue[]>(initialSnapshot.planningIssues ?? []);
  const [assignments, setAssignments] = useState<Assignment[]>(initialSnapshot.assignments ?? []);
  const [sprintPlan, setSprintPlan] = useState<SprintDecision[]>(initialSnapshot.sprintPlan ?? []);
  const [sprintScope, setSprintScope] = useState<SprintScopeReview | null>(null);
  const [sprintScopeTaskIds, setSprintScopeTaskIds] = useState<string[]>([]);
  const [sprintScopeReviewer, setSprintScopeReviewer] = useState("");
  const [sprintScopeNote, setSprintScopeNote] = useState("");
  const [duplicateCandidates, setDuplicateCandidates] = useState<DuplicateCandidate[]>(initialSnapshot.duplicateCandidates ?? []);
  const [duplicatesComplete, setDuplicatesComplete] = useState(initialSnapshot.duplicatesComplete ?? false);
  const [qualityResults, setQualityResults] = useState<QualityResult[]>(initialSnapshot.qualityResults ?? []);
  const [qualityClarifications, setQualityClarifications] = useState<QualityClarification[]>([]);
  const [qualityAnswerDrafts, setQualityAnswerDrafts] = useState<Record<string, Record<string, string>>>({});
  const [newStoryDraft, setNewStoryDraft] = useState({ title: "", user_story: "", description: "", priority: "Medium", story_points: "5", acceptance_criteria: "", definition_of_done: "", source_references: "" });
  const [newStoryCheck, setNewStoryCheck] = useState<NewStoryCheck | null>(null);
  const [boardHealth, setBoardHealth] = useState<BoardHealth | null>(initialSnapshot.boardHealth ?? null);
  const [approved, setApproved] = useState(initialSnapshot.approved ?? false);
  const [reviewer, setReviewer] = useState(initialSnapshot.reviewer ?? "");
  const [reviewNote, setReviewNote] = useState(initialSnapshot.reviewNote ?? "");
  const [publishedExport, setPublishedExport] = useState<PublishedExport | null>(initialSnapshot.publishedExport ?? null);
  const [selectedOption, setSelectedOption] = useState(initialSnapshot.selectedOption ?? "");
  const [customAnswer, setCustomAnswer] = useState(initialSnapshot.customAnswer ?? "");
  const [name, setName] = useState(initialSnapshot.name ?? "");
  const [description, setDescription] = useState(initialSnapshot.description ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const agentRailRef = useRef<HTMLElement | null>(null);

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
  const unlockedAgent = publishedExport || approved ? 16
    : boardHealth ? 15
      : qualityClarifications.some((item) => item.status === "pending") ? 13
        : qualityResults.length > 0 ? 14
        : duplicatesComplete ? 13
        : sprintPlan.length > 0 ? 12
          : assignments.length > 0 ? 11
            : planningReady ? 10
              : dependencies !== null && estimationBrief ? 9
                : estimated ? 8
                  : enriched ? 7
                    : backlog ? 6
                      : decompositions.length > 0 ? 5
                        : requirements.length > 0 ? 4
                          : clarificationsComplete ? 3
                            : session ? 2
                              : analysisJob ? 2
                                : document ? 1
                                  : 0;
  const visibleAgent = selectedAgent < 0
    ? unlockedAgent
    : Math.min(selectedAgent, unlockedAgent);
  const currentAgent = agentStages[visibleAgent];
  const workflowProgress = Math.round(((unlockedAgent + 1) / agentStages.length) * 100);
  const latestAgentProposal = [...agentMessages].reverse().find((message) => message.role === "assistant");
  const boardHealthAvailable = boardHealth !== null;

  useEffect(() => {
    const activeAgent = agentRailRef.current?.querySelector<HTMLElement>(`[data-agent-index="${visibleAgent}"]`);
    activeAgent?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [visibleAgent, busy]);

  useEffect(() => {
    if (!session || visibleAgent < 14 || !boardHealthAvailable) return;
    fetch(`${API_URL}/sessions/${session.id}/board-health`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not refresh board health.");
        return response.json();
      })
      .then((result: { health: BoardHealth }) => setBoardHealth(result.health))
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not refresh board health."));
  }, [session, visibleAgent, publishedExport, boardHealthAvailable]);

  useEffect(() => {
    if (!hydrated) return;
    const snapshot: WorkflowSnapshot = {
      authenticated,
      selectedStage: visibleStage,
      selectedAgent: visibleAgent,
      documents,
      project, document, analysisJob, session, llmUsage, clarification,
      clarificationsComplete, requirements, decompositions, backlog, enriched,
      estimated, dependencies, planningReady, planningIssues, assignments,
      sprintPlan, duplicateCandidates, duplicatesComplete, qualityResults, boardHealth, reviewer,
      reviewNote, approved, publishedExport, selectedOption, customAnswer, name, description,
    };
    try {
      window.localStorage.setItem(WORKFLOW_STORAGE_KEY, JSON.stringify(snapshot));
    } catch {
      window.localStorage.removeItem(WORKFLOW_STORAGE_KEY);
    }
  }, [
    hydrated, authenticated, visibleStage, visibleAgent, project, document, documents, analysisJob, session, llmUsage,
    clarification, clarificationsComplete, requirements, decompositions, backlog,
    enriched, estimated, dependencies, planningReady, planningIssues, assignments,
    sprintPlan, duplicateCandidates, duplicatesComplete, qualityResults, boardHealth, reviewer,
    reviewNote, approved, publishedExport, selectedOption, customAnswer, name, description,
  ]);

  useEffect(() => {
    if (!hydrated) return;
    fetch(`${API_URL}/projects`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not load project history.");
        return response.json();
      })
      .then((items: Project[]) => setProjectHistory(items))
      .catch((cause) => {
        setProjectHistory([]);
        setError(cause instanceof Error ? cause.message : "Could not load project history.");
      });
  }, [hydrated]);

  useEffect(() => {
    if (!session) {
      return;
    }
    if (assignments.length === 0 && sprintPlan.length === 0) {
      return;
    }
    fetch(`${API_URL}/sessions/${session.id}/sprint-scope-review`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not load Sprint scope review.");
        return response.json();
      })
      .then((review: SprintScopeReview) => {
        setSprintScope(review);
        setSprintScopeTaskIds(review.selected_task_ids);
        setSprintScopeReviewer(review.reviewed_by);
        setSprintScopeNote(review.note);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load Sprint scope review."));
  }, [session, assignments, sprintPlan]);

  useEffect(() => {
    if (!session) {
      return;
    }
    fetch(`${API_URL}/sessions/${session.id}/quality-clarifications`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not load quality clarifications.");
        return response.json();
      })
      .then((items: QualityClarification[]) => setQualityClarifications(items))
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load quality clarifications."));
  }, [session, qualityResults]);

  useEffect(() => {
    if (!session) {
      return;
    }
    fetch(`${API_URL}/sessions/${session.id}/dependency-order`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not load Dependency Epic ordering.");
        return response.json();
      })
      .then((workspace: EstimationBriefWorkspace) => {
        setEstimationBrief(workspace.brief);
        setEstimationOptions({ epics: workspace.epics, parallel_groups: workspace.parallel_groups, parallelism_note: workspace.parallelism_note });
        setEstimationDraft(workspace.brief ?? {
          ...emptyEstimationBrief,
          ranked_epic_ids: workspace.epics.map((item) => item.stable_id),
        });
      })
      .catch((cause) => {
        setEstimationBrief(null);
          setError(cause instanceof Error ? cause.message : "Could not load Dependency Epic ordering.");
      });
        }, [session, dependencies]);

  useEffect(() => {
    if (!session) {
      return;
    }
    fetch(`${API_URL}/sessions/${session.id}/clarifications`)
      .then((response) => {
        if (!response.ok) throw new Error("Could not load clarification history.");
        return response.json();
      })
      .then((items: ClarificationHistory[]) => setClarificationHistory(items))
      .catch((cause) => {
        setClarificationHistory([]);
        setError(cause instanceof Error ? cause.message : "Could not load clarification history.");
      });
  }, [session, clarification, clarificationsComplete]);

  useEffect(() => {
    if (!session) {
      return;
    }
    fetch(`${API_URL}/sessions/${session.id}/agents/${encodeURIComponent(currentAgent.label)}/messages`)
      .then((response) => {
        if (!response.ok) throw new Error(`Could not load ${currentAgent.label} review messages.`);
        return response.json();
      })
      .then((items: AgentMessage[]) => setAgentMessages(items))
      .catch((cause) => {
        setAgentMessages([]);
        setError(cause instanceof Error ? cause.message : "Could not load agent review messages.");
      });
  }, [session, currentAgent.label]);

  function navigateToAgent(index: number) {
    if (index > unlockedAgent || index === visibleAgent) return;
    const agent = agentStages[index];
    setTransitionDirection(index > visibleAgent ? "forward" : "backward");
    setSelectedAgent(index);
    setSelectedStage(agent.section);
    setHomeOpen(false);
    window.requestAnimationFrame(() => {
      const target = window.document.getElementById(agent.target)
        ?? window.document.getElementById(`workflow-stage-${agent.section}`);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function scrollAgentRail(direction: -1 | 1) {
    agentRailRef.current?.scrollBy({
      left: direction * Math.max(320, agentRailRef.current.clientWidth * 0.7),
      behavior: "smooth",
    });
  }

  async function openHistoryProject(item: Project) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/projects/${item.id}/documents`);
      if (!response.ok) throw new Error("Could not load project architectures.");
      setHistoryProject(item);
      setDeleteProjectArmed(false);
      setHistoryDocuments(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function inspectDocumentChunks(item: Document) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/documents/${item.id}/chunks`);
      if (!response.ok) throw new Error("Could not load extracted chunks.");
      setSelectedChunkDocument(item);
      setDocumentChunks(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function sendAgentPrompt(event: FormEvent) {
    event.preventDefault();
    if (!session || !agentPrompt.trim()) return;
    setAgentPromptBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/agents/${encodeURIComponent(currentAgent.label)}/prompt`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: agentPrompt.trim() }),
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "The agent could not review this feedback.");
      }
      setAgentPrompt("");
      const historyResponse = await fetch(`${API_URL}/sessions/${session.id}/agents/${encodeURIComponent(currentAgent.label)}/messages`);
      if (!historyResponse.ok) throw new Error("The review completed, but its conversation could not be refreshed.");
      setAgentMessages(await historyResponse.json());
      await loadLlmUsage(session.id);
      window.requestAnimationFrame(() => {
        window.document.getElementById("agent-review-proposal")?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setAgentPromptBusy(false);
    }
  }

  async function continueHistoryProject() {
    if (!historyProject) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/projects/${historyProject.id}/resume`);
      if (!response.ok) throw new Error("Could not resume this project.");
      const resumed = await response.json() as WorkflowResume;
      const lastDocument = resumed.documents.at(-1) ?? null;
      const documentsProcessed = resumed.documents.length > 0 && resumed.documents.every((item) => item.status === "processed");
      setProject(resumed.project);
      setDocuments(resumed.documents);
      setDocument(lastDocument);
      setAnalysisJob(documentsProcessed ? { id: "persisted", status: "completed", progress: 100, error: null } : null);
      setSession(resumed.session);
      setLlmUsage(null);
      setClarification(resumed.clarification);
      setClarificationsComplete(resumed.clarifications_complete);
      setRequirements(resumed.requirements);
      setDecompositions(resumed.decompositions);
      setBacklog(resumed.backlog ? { ...resumed.backlog, features: resumed.backlog.features ?? [] } : null);
      setEnriched(resumed.enriched);
      setEstimated(resumed.estimated);
      setDependencies(resumed.dependencies);
      setPlanningReady(resumed.planning_ready);
      setPlanningIssues([]);
      setAssignments(resumed.assignments);
      setSprintPlan(resumed.sprint_plan);
      setDuplicateCandidates(resumed.duplicate_candidates);
      setDuplicatesComplete(resumed.duplicates_complete);
      setQualityResults(resumed.quality_results);
      setBoardHealth(resumed.board_health);
      setApproved(resumed.approved);
      setPublishedExport(resumed.published_export);
      setReviewer("");
      setReviewNote("");
      setSelectedOption("");
      setCustomAnswer("");
      setSelectedAgent(resumed.agent_index);
      setSelectedStage(agentStages[resumed.agent_index]?.section ?? 0);
      setHistoryProject(null);
      setHomeOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function deleteHistoryProject() {
    if (!historyProject) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/projects/${historyProject.id}`, { method: "DELETE" });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Could not delete the project.");
      }
      const deletedId = historyProject.id;
      setProjectHistory((items) => items.filter((item) => item.id !== deletedId));
      setHistoryProject(null);
      setHistoryDocuments([]);
      setDeleteProjectArmed(false);
      if (project?.id === deletedId) {
        startNewProject();
        setHomeOpen(true);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  function startNewProject() {
    window.localStorage.removeItem(WORKFLOW_STORAGE_KEY);
    setHomeOpen(false);
    setSelectedStage(0);
    setSelectedAgent(0);
    setProject(null);
    setDocument(null);
    setDocuments([]);
    setAnalysisJob(null);
    setSelectedChunkDocument(null);
    setDocumentChunks([]);
    setClarificationHistory([]);
    setAgentMessages([]);
    setAgentPrompt("");
    setSession(null);
    setLlmUsage(null);
    setClarification(null);
    setClarificationsComplete(false);
    setRequirements([]);
    setDecompositions([]);
    setBacklog(null);
    setEnriched(false);
    setEstimated(false);
    setDependencies(null);
    setPlanningReady(false);
    setPlanningIssues([]);
    setAssignments([]);
    setSprintPlan([]);
    setDuplicateCandidates([]);
    setDuplicatesComplete(false);
    setQualityResults([]);
    setBoardHealth(null);
    setApproved(false);
    setReviewer("");
    setReviewNote("");
    setPublishedExport(null);
    setSelectedOption("");
    setCustomAnswer("");
    setName("");
    setDescription("");
    setError("");
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
      const created = await response.json() as Project;
      setProject(created);
      setProjectHistory((items) => [created, ...items.filter((item) => item.id !== created.id)]);
      setHomeOpen(false);
      setSelectedAgent(0);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function uploadDocument(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0 || !project) return;
    setBusy(true);
    setError("");
    try {
      const uploaded: Document[] = [];
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        const response = await fetch(
          `${API_URL}/projects/${project.id}/documents`,
          { method: "POST", body: form },
        );
        if (!response.ok) {
          const body = await response.json();
          throw new Error(body.detail ?? `Could not upload ${file.name}.`);
        }
        uploaded.push(await response.json());
      }
      setDocuments((items) => [...items, ...uploaded]);
      setDocument(uploaded.at(-1) ?? null);
      setSelectedAgent(1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function beginAnalysis() {
    const pendingDocuments = documents.filter((item) => item.status !== "processed");
    if (pendingDocuments.length === 0) return;
    setBusy(true);
    setError("");
    try {
      for (const item of pendingDocuments) {
        const response = await fetch(
          `${API_URL}/documents/${item.id}/process`,
          { method: "POST" },
        );
        if (!response.ok) {
          const body = await response.json();
          throw new Error(body.detail ?? `Analysis failed for ${item.original_name}.`);
        }
        setAnalysisJob(await response.json());
        setDocuments((items) => items.map((candidate) =>
          candidate.id === item.id ? { ...candidate, status: "processed" } : candidate,
        ));
        setDocument((current) => current?.id === item.id ? { ...current, status: "processed" } : current);
      }
      setSelectedStage(0);
      setSelectedAgent(1);
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

  async function waitForSessionPreparation(sessionId: string): Promise<AnalysisSession> {
    for (let attempt = 0; attempt < 450; attempt += 1) {
      const response = await fetch(`${API_URL}/sessions/${sessionId}`);
      if (!response.ok) throw new Error("Could not check analysis preparation status.");
      const current = await response.json() as AnalysisSession;
      setSession(current);
      if (current.status === "failed") throw new Error("Requirement or clarification preparation failed. Review the global error and retry.");
      if (!current.status.startsWith("processing_")) return current;
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }
    throw new Error("Preparation is still running after 15 minutes. You can safely resume this project from History.");
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
      setSelectedAgent(2);
      const prepared = created.status.startsWith("processing_")
        ? await waitForSessionPreparation(created.id)
        : created;
      if (prepared.status !== "awaiting_clarification" && prepared.status !== "clarifications_complete") {
        throw new Error(`Unexpected preparation status: ${prepared.status}.`);
      }
      if (prepared.status === "awaiting_clarification") await loadNextClarification(created.id);
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
      setSelectedAgent(4);
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
      setSelectedAgent(4);
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
      setSelectedAgent(5);
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
      setSelectedAgent(6);
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
      setSelectedAgent(7);
      await loadLlmUsage(session.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function saveEstimationBrief(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    if (!estimationDraft.answered_by.trim()) {
      setError("Enter the decision owner before saving the Epic order.");
      return;
    }
    if (estimationDraft.ranked_epic_ids.length !== estimationOptions.epics.length) {
      setError("Rank every generated Epic before continuing to planning.");
      return;
    }
    if (!estimationDraft.priority_rationale.trim()) {
      setError("Explain the Product Owner prioritization rationale.");
      return;
    }
    setEstimationBriefBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/dependency-order`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...estimationDraft,
          answered_by: estimationDraft.answered_by.trim(),
        }),
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Could not save the Dependency Epic order.");
      }
      const saved = await response.json() as EstimationBrief;
      setEstimationBrief(saved);
      setEstimationDraft(saved);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save the Dependency Epic order.");
    } finally {
      setEstimationBriefBusy(false);
    }
  }

  function moveRankedEpic(index: number, direction: -1 | 1) {
    setEstimationDraft((current) => {
      const target = index + direction;
      if (target < 0 || target >= current.ranked_epic_ids.length) return current;
      const ranked = [...current.ranked_epic_ids];
      [ranked[index], ranked[target]] = [ranked[target], ranked[index]];
      return { ...current, ranked_epic_ids: ranked };
    });
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
      setEstimationBrief(null);
      setSelectedAgent(8);
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
      if (result.requires_clarification) {
        const blockingIssues = result.issues
          .filter((issue) => issue.blocking)
          .map((issue) => `${issue.sheet}${issue.row ? ` row ${issue.row}` : ""}: ${issue.message}`);
        setSession((current) => current ? { ...current, status: "dependencies_complete", current_node: "Planning Data" } : current);
        setSelectedStage(4);
        setSelectedAgent(9);
        setError(`Planning data was checked but not imported. Fix these blocking issues: ${blockingIssues.join(" ")}`);
      } else {
        setSession((current) => current ? { ...current, status: "planning_data_ready", current_node: "Assignment" } : current);
        setAssignments([]);
        setSprintPlan([]);
        setSprintScope(null);
        setDuplicateCandidates([]);
        setDuplicatesComplete(false);
        setQualityResults([]);
        setQualityClarifications([]);
        setBoardHealth(null);
        setApproved(false);
        setPublishedExport(null);
        setSelectedStage(4);
        setSelectedAgent(10);
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
      const result = await postAgent<{ assignments: Assignment[] }>(session.id, "assign");
      setAssignments(result.assignments);
      await loadLlmUsage(session.id);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Unexpected error";
      if (message.includes("Verified team capacity is insufficient")) {
        setPlanningReady(false);
        setAssignments([]);
        setSprintPlan([]);
        setSprintScope(null);
        setDuplicateCandidates([]);
        setDuplicatesComplete(false);
        setQualityResults([]);
        setQualityClarifications([]);
        setBoardHealth(null);
        setApproved(false);
        setPublishedExport(null);
        setPlanningIssues([{
          sheet: "Planning Data", row: null, field: "capacity_hours",
          message: "Available team capacity is below the estimated Task demand. Upload a revised planning workbook with additional capacity, members, allocation, or Sprints.",
          blocking: true,
        }]);
        setSelectedAgent(9);
      }
      setError(message);
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

  async function runSprintPlanning() {
    if (!session) return;
    if (!sprintScope?.reviewed) {
      setError("Review and save the approved Task scope before planning Sprints.");
      return;
    }
    setBusy(true); setError("");
    try {
      const result = await postAgent<{ decisions: SprintDecision[] }>(session.id, "plan-sprints");
      setSprintPlan(result.decisions);
      await loadLlmUsage(session.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
  }

  async function saveSprintScopeReview(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    if (!sprintScopeReviewer.trim()) {
      setError("Enter the scope reviewer name.");
      return;
    }
    if (sprintScopeTaskIds.length === 0) {
      setError("Select at least one Task for Sprint planning.");
      return;
    }
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/sprint-scope-review`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewed_by: sprintScopeReviewer.trim(), selected_task_ids: sprintScopeTaskIds, note: sprintScopeNote.trim() }),
      });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail ?? "Could not save Sprint scope review."); }
      const saved = await response.json() as SprintScopeReview;
      setSprintScope(saved);
      setSprintScopeTaskIds(saved.selected_task_ids);
      setSprintPlan([]);
      setDuplicateCandidates([]);
      setDuplicatesComplete(false);
      setQualityResults([]);
      setQualityClarifications([]);
      setBoardHealth(null);
      setApproved(false);
      setPublishedExport(null);
      setSelectedAgent(11);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
  }

  async function runDuplicateDetection() {
    if (!session) return;
    setBusy(true); setError("");
    try {
      const result = await postAgent<{ candidates: DuplicateCandidate[] }>(session.id, "duplicates");
      setDuplicateCandidates(result.candidates); setDuplicatesComplete(true);
      await loadLlmUsage(session.id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
  }

  async function runQualityValidation() {
    if (!session) return;
    setBusy(true); setError("");
    try {
      const result = await postAgent<{ results: QualityResult[]; clarifications: QualityClarification[] }>(session.id, "quality");
      setQualityResults(result.results);
      setQualityClarifications(result.clarifications);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
  }

  async function answerQualityClarification(item: QualityClarification) {
    const draft = qualityAnswerDrafts[item.id] ?? {};
    const listFields = new Set(["source_references", "acceptance_criteria", "definition_of_done"]);
    const numericFields = new Set(["story_points", "estimated_hours"]);
    const values = Object.fromEntries(item.missing_fields.map((check) => {
      const field = check === "source_traceable" ? "source_references"
        : check === "priority_set" ? "priority"
          : check === "estimated" ? item.item_type === "story" ? "story_points" : "estimated_hours"
            : check.replace(/_present$/, "");
      const raw = draft[field] ?? "";
      return [field, listFields.has(field) ? raw.split("\n").map((value) => value.trim()).filter(Boolean) : numericFields.has(field) ? Number(raw) : raw];
    }));
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/quality-clarifications/${item.id}/answer`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ values }),
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail ?? "Could not record quality clarification.");
      }
      const answered = await response.json() as QualityClarification;
      const updated = qualityClarifications.map((candidate) => candidate.id === answered.id ? answered : candidate);
      setQualityClarifications(updated);
      if (updated.every((candidate) => candidate.status === "answered")) setQualityResults([]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
  }

  async function checkProposedStory(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    setBusy(true); setError(""); setNewStoryCheck(null);
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/new-story-check`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...newStoryDraft,
          story_points: Number(newStoryDraft.story_points),
          acceptance_criteria: newStoryDraft.acceptance_criteria.split("\n").map((value) => value.trim()).filter(Boolean),
          definition_of_done: newStoryDraft.definition_of_done.split("\n").map((value) => value.trim()).filter(Boolean),
          source_references: newStoryDraft.source_references.split("\n").map((value) => value.trim()).filter(Boolean),
        }),
      });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail ?? "New-story check failed."); }
      setNewStoryCheck(await response.json());
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
  }

  async function confirmNewStory() {
    if (!session || !newStoryCheck || newStoryCheck.classification !== "new") return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/stories`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ check_id: newStoryCheck.id, confirmed: true }),
      });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail ?? "Story creation failed."); }
      setNewStoryCheck({ ...newStoryCheck, status: "created" });
      if (project) {
        const resumed = await fetch(`${API_URL}/projects/${project.id}/resume`).then((result) => result.json()) as WorkflowResume;
        setBacklog(resumed.backlog ? { ...resumed.backlog, features: resumed.backlog.features ?? [] } : null);
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
  }

  async function runBoardHealthAssessment() {
    if (!session) return;
    setBusy(true); setError("");
    try {
      const result = await postAgent<{ health: BoardHealth }>(session.id, "board-health");
      setBoardHealth(result.health);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
  }

  async function runPublication() {
    if (!session || !approved) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_URL}/sessions/${session.id}/publish`, { method: "POST" });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail ?? "Workbook publication failed.");
      }
      setPublishedExport(await response.json());
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unexpected error"); }
    finally { setBusy(false); }
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
        setApproved(true);
      } else {
        setBoardHealth(null);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  function signIn(event: FormEvent) {
    event.preventDefault();
    if (loginUsername.trim().toLowerCase() !== "admin" || loginPassword !== "password") {
      setLoginError("The username or password is incorrect.");
      return;
    }
    setLoginError("");
    setLoginPassword("");
    setAuthenticated(true);
  }

  function signOut() {
    setAuthenticated(false);
    setLoginPassword("");
    setLoginError("");
  }

  const currentJob = (() => {
    if (busy) {
      const label = session?.status === "processing_requirements"
        ? "Extracting requirements..."
        : session?.status === "processing_clarifications"
          ? "Preparing clarifications..."
          : "Job running...";
      return { label, action: () => undefined, disabled: true };
    }
    switch (visibleAgent) {
      case 1:
        if (documents.some((item) => item.status !== "processed")) return { label: "Analyze documents", action: beginAnalysis, disabled: false };
        if (!session) return { label: "Start clarification", action: startClarification, disabled: false };
        return null;
      case 3:
        return requirements.length === 0 ? { label: "Generate requirements", action: generateRequirements, disabled: false } : null;
      case 4:
        return decompositions.length === 0 ? { label: "Run decomposition", action: runDecomposition, disabled: false } : null;
      case 5:
        return !backlog ? { label: "Build backlog", action: runBacklog, disabled: false } : null;
      case 6:
        return !enriched ? { label: "Enrich backlog", action: runEnrichment, disabled: false } : null;
      case 7:
        return !estimated ? { label: "Estimate backlog", action: runEstimation, disabled: false } : null;
      case 8:
        return dependencies === null ? { label: "Analyze dependencies", action: runDependencies, disabled: false }
          : !estimationBrief ? { label: "Save Epic order below", action: () => undefined, disabled: true } : null;
      case 9:
        return !planningReady ? { label: planningIssues.some((item) => item.field === "capacity_hours") ? "Upload revised planning data" : "Upload planning data", action: () => window.document.getElementById("planning-data-upload")?.click(), disabled: false } : null;
      case 10:
        return assignments.length === 0 ? { label: "Recommend assignments", action: runAssignment, disabled: !planningReady } : null;
      case 11:
        return sprintPlan.length === 0
          ? { label: sprintScope?.reviewed ? "Plan approved scope" : "Review Task scope below", action: runSprintPlanning, disabled: assignments.length === 0 || !sprintScope?.reviewed }
          : null;
      case 12:
        return !duplicatesComplete ? { label: "Check duplicates", action: runDuplicateDetection, disabled: sprintPlan.length === 0 } : null;
      case 13:
        return qualityResults.length === 0 ? { label: "Validate 85% readiness", action: runQualityValidation, disabled: !duplicatesComplete } : null;
      case 14:
        return !boardHealth ? { label: "Assess board health", action: runBoardHealthAssessment, disabled: qualityResults.length === 0 || qualityResults.some((item) => !item.passed) } : null;
      case 16:
        return !publishedExport ? { label: "Publish approved workbook", action: runPublication, disabled: !approved } : null;
      default:
        return null;
    }
  })();

  if (!hydrated) {
    return <div className="min-h-screen bg-[var(--canvas)]" aria-label="Loading Sprint Sarthi" />;
  }

  if (!authenticated) {
    return (
      <main className="login-shell">
        <section className="login-panel" aria-labelledby="login-title">
          <div className="login-brand">
            <span className="login-brand__mark"><Bot size={24} /></span>
            <span>
              <strong>Sprint Sarthi</strong>
              <small>Human-governed AI Scrum Master</small>
            </span>
          </div>

          <div className="login-panel__content">
            <span className="login-kicker">Secure workspace</span>
            <h1 id="login-title">Welcome back.</h1>
            <p>Sign in to continue planning with your governed agent team.</p>

            <form className="login-form" onSubmit={signIn}>
              <label htmlFor="login-username">Username</label>
              <div className="login-input-wrap">
                <UserRound size={18} aria-hidden="true" />
                <input id="login-username" value={loginUsername} onChange={(event) => setLoginUsername(event.target.value)} autoComplete="username" placeholder="Enter your username" required />
              </div>

              <label htmlFor="login-password">Password</label>
              <div className="login-input-wrap">
                <LockKeyhole size={18} aria-hidden="true" />
                <input id="login-password" type={showLoginPassword ? "text" : "password"} value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} autoComplete="current-password" placeholder="Enter your password" required />
                <button type="button" onClick={() => setShowLoginPassword((visible) => !visible)} aria-label={showLoginPassword ? "Hide password" : "Show password"}>
                  {showLoginPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              {loginError && <p className="login-error" role="alert">{loginError}</p>}
              <button className="login-submit" type="submit">Sign in <LogIn size={17} /></button>
            </form>

            <p className="login-demo"><strong>Demo access</strong><span>admin / password</span></p>
          </div>

          <p className="login-panel__footer"><ShieldCheck size={15} /> Human approval remains required before publication.</p>
        </section>

        <section className="login-scene" aria-label="Animated global collaboration illustration">
          <iframe src="/siddesh.html" title="Sprint Sarthi animated globe" tabIndex={-1} />
          <div className="login-scene__shade" aria-hidden="true" />
        </section>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--canvas)] text-[var(--ink)]">
      <header className="sticky top-0 z-50 border-b border-[var(--line)] bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-[72px] max-w-[1440px] items-center gap-5 px-5 lg:px-8">
          <button type="button" onClick={() => setHomeOpen(true)} className="flex shrink-0 items-center gap-3 text-left" aria-label="Sprint Sarthi home">
            <span className="relative grid size-10 place-items-center bg-[var(--ink)] text-white">
              <Bot size={21} />
              <span aria-hidden="true" className="absolute inset-x-0 bottom-0 h-1 bg-[var(--accent)]" />
            </span>
            <span>
              <strong className="block font-display text-lg leading-tight">Sprint Sarthi</strong>
              <span className="hidden text-[11px] text-[var(--muted)] sm:block">Human-governed AI Scrum Master</span>
            </span>
          </button>

          <div className="hidden min-w-0 flex-1 items-center gap-5 border-l border-[var(--line)] pl-5 md:flex">
            <div className="min-w-0">
              <span className="text-[10px] font-bold uppercase text-[var(--muted)]">Active project</span>
              <p className="truncate text-sm font-semibold">{project?.name ?? "No project selected"}</p>
            </div>
            <span aria-hidden="true" className="h-8 w-px bg-[var(--line)]" />
            <div className="min-w-0">
              <span className="text-[10px] font-bold uppercase text-[var(--muted)]">{homeOpen ? "Workspace" : `Agent ${visibleAgent + 1} of ${agentStages.length}`}</span>
              <p className="truncate text-sm font-semibold text-[var(--accent)]">{homeOpen ? "Project history" : currentAgent.label}</p>
            </div>
          </div>

          <div className="ml-auto flex shrink-0 items-center gap-2">
            <span className="hidden items-center gap-2 border-r border-[var(--line)] pr-3 text-xs font-semibold text-[var(--success)] lg:flex" title="Publication requires named human approval">
              <ShieldCheck size={16} /> Human governed
            </span>
            <button type="button" onClick={() => setHomeOpen(true)} className={`flex h-10 items-center gap-2 border px-3 text-xs font-bold ${homeOpen ? "border-[var(--ink)] bg-[var(--ink)] text-white" : "border-[var(--line-strong)] bg-white"}`} aria-label="Project history" title="Project history">
              <HomeIcon size={16} /> <span className="hidden sm:inline">History</span>
            </button>
            <button type="button" onClick={startNewProject} className="flex h-10 items-center gap-2 bg-[var(--accent)] px-3 text-xs font-bold text-white">
              <Plus size={16} /> <span className="hidden sm:inline">New project</span>
            </button>
            <button type="button" onClick={signOut} className="grid size-10 place-items-center border border-[var(--line-strong)] bg-white" aria-label="Sign out" title="Sign out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
        {!homeOpen && (
          <div className="absolute inset-x-0 bottom-0 h-0.5 bg-[var(--line)]" aria-hidden="true">
            <div className="h-full bg-[var(--accent)] transition-[width] duration-500" style={{ width: `${workflowProgress}%` }} />
          </div>
        )}
      </header>
      {error && (
        <div className="sticky top-[72px] z-40 border-b border-red-200 bg-red-50" role="alert" aria-live="assertive">
          <div className="mx-auto flex max-w-[1440px] items-start gap-3 px-5 py-3 text-sm text-red-900 lg:px-8">
            <span className="mt-0.5 grid size-5 shrink-0 place-items-center bg-red-700 text-xs font-bold text-white">!</span>
            <p className="min-w-0 flex-1"><strong>Something went wrong.</strong> {error}</p>
            <button type="button" onClick={() => setError("")} className="grid size-7 shrink-0 place-items-center text-red-800" aria-label="Dismiss error" title="Dismiss error">
              <X size={16} />
            </button>
          </div>
        </div>
      )}
      <main className="mx-auto max-w-[1440px] px-5 py-8 lg:px-8">
        <section className="mb-8 grid gap-6 border-b border-[var(--line)] pb-8 md:grid-cols-[minmax(0,1fr)_minmax(360px,460px)] md:items-center lg:gap-10">
          <div className="py-2">
            <p className="mb-2 text-xs font-bold uppercase text-[var(--accent)]">
              {homeOpen ? "Project portfolio" : `Agent ${visibleAgent + 1} of ${agentStages.length}`}
            </p>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">
              {homeOpen ? "Your project history" : currentAgent.label}
            </h1>
            <p className="mt-3 max-w-2xl text-[var(--muted)]">
              {homeOpen
                ? "Open a saved project to inspect its current state or continue from the last persisted agent."
                : currentAgent.description}
            </p>
          </div>
          <div className="relative aspect-[16/9] min-h-44 overflow-hidden border border-[var(--line)] bg-[var(--soft)] shadow-[8px_8px_0_var(--line)] md:min-h-0">
            <div aria-hidden="true" className="absolute inset-0 bg-cover bg-center transition-[background-image] duration-300" style={{ backgroundImage: `url(${currentAgent.image})` }} />
            <div aria-hidden="true" className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/10" />
            <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-4 p-4 text-white">
              <div>
                <span className="text-[10px] font-bold uppercase text-white/75">Current agent</span>
                <p className="mt-0.5 font-display text-xl font-semibold">{currentAgent.label}</p>
              </div>
              <span className="mb-1 flex shrink-0 items-center gap-2 text-xs font-semibold">
                <span className="size-2 bg-[var(--success)]" /> Live state
              </span>
            </div>
          </div>
        </section>
        {homeOpen ? (
          <section className="border-y border-[var(--line)] bg-white py-6">
            <div className="flex flex-wrap items-end justify-between gap-4 px-5 sm:px-7">
              <div>
                <span className="text-xs font-bold uppercase text-[var(--accent)]">Home</span>
                <h2 className="mt-1 font-display text-2xl font-semibold">Project history</h2>
                <p className="mt-2 text-sm text-[var(--muted)]">Projects are loaded from the SQLite system of record.</p>
              </div>
              <button type="button" onClick={startNewProject} className="flex h-10 items-center gap-2 bg-[var(--accent)] px-4 text-sm font-bold text-white">
                <Plus size={16} /> Create project
              </button>
            </div>
            {historyProject && (
              <div className="mx-5 mt-6 border border-[var(--line-strong)] bg-[var(--soft)] p-5 sm:mx-7">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold uppercase text-[var(--accent)]">Selected project</span>
                    <h3 className="mt-1 font-display text-xl font-semibold">{historyProject.name}</h3>
                    <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">{historyProject.description || "No objective provided."}</p>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={continueHistoryProject} disabled={busy} className="flex h-9 items-center gap-2 bg-[var(--ink)] px-3 text-xs font-bold text-white disabled:opacity-60">
                      {busy ? <Loader2 className="animate-spin" size={14} /> : <ArrowRight size={14} />}
                      Continue workflow
                    </button>
                    <button type="button" onClick={() => setHistoryProject(null)} className="h-9 border border-[var(--line-strong)] bg-white px-3 text-xs font-bold">Close</button>
                    <button type="button" onClick={() => setDeleteProjectArmed(true)} disabled={busy} className="grid size-9 place-items-center border border-red-300 bg-red-50 text-red-800 disabled:opacity-50" aria-label={`Delete ${historyProject.name}`} title="Delete project"><Trash2 size={15} /></button>
                  </div>
                </div>
                {deleteProjectArmed && (
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-l-4 border-red-600 bg-red-50 p-4 text-sm text-red-950" role="alert">
                    <p><strong>Delete {historyProject.name} permanently?</strong> Its workflow history, backlog, planning data, and stored project files will be removed.</p>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => setDeleteProjectArmed(false)} disabled={busy} className="h-9 border border-red-300 bg-white px-3 text-xs font-bold disabled:opacity-50">Cancel</button>
                      <button type="button" onClick={deleteHistoryProject} disabled={busy} className="flex h-9 items-center gap-2 bg-red-700 px-3 text-xs font-bold text-white disabled:opacity-50">{busy ? <Loader2 className="animate-spin" size={14} /> : <Trash2 size={14} />} Confirm deletion</button>
                    </div>
                  </div>
                )}
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {historyDocuments.length === 0 ? (
                    <p className="text-sm text-[var(--muted)]">No architecture documents uploaded.</p>
                  ) : historyDocuments.map((item) => (
                    <div key={item.id} className="flex items-center justify-between gap-3 border border-[var(--line)] bg-white px-3 py-2 text-xs">
                      <span className="truncate font-semibold">{item.original_name}</span>
                      <span className="shrink-0 capitalize text-[var(--muted)]">{item.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {projectHistory.length === 0 ? (
              <div className="mx-5 mt-6 border border-dashed border-[var(--line-strong)] bg-[var(--soft)] p-8 text-center sm:mx-7">
                <FolderOpen className="mx-auto text-[var(--muted)]" size={28} />
                <p className="mt-3 text-sm font-semibold">No project history yet</p>
              </div>
            ) : (
              <div className="mt-6 grid gap-px border-y border-[var(--line)] bg-[var(--line)] sm:grid-cols-2 lg:grid-cols-3">
                {projectHistory.map((item) => (
                  <button type="button" key={item.id} onClick={() => openHistoryProject(item)} disabled={busy} className="bg-white p-5 text-left outline-none hover:bg-[var(--soft)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)] disabled:opacity-60">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-display text-lg font-semibold">{item.name}</h3>
                        <p className="mt-1 line-clamp-2 text-sm text-[var(--muted)]">{item.description || "No objective provided."}</p>
                      </div>
                      <span className="max-w-40 bg-[var(--soft)] px-2 py-1 text-right text-xs font-bold">{item.workflow_state ?? item.status}</span>
                    </div>
                    <p className="mt-5 text-xs text-[var(--muted)]">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : "Saved project"}
                    </p>
                    <span className="mt-4 flex items-center gap-2 text-xs font-bold text-[var(--accent)]">
                      Open project <ArrowRight size={14} />
                    </span>
                  </button>
                ))}
              </div>
            )}
          </section>
        ) : (
          <>
        <div className="agent-rail-shell border border-[var(--line)] bg-white">
          <div className="agent-rail-toolbar">
            <div className="agent-rail-state" aria-live="polite">
              <span className={`agent-rail-state__dot ${busy ? "agent-rail-state__dot--running" : ""}`} />
              <span>{busy ? `${currentAgent.label} running` : `${unlockedAgent + 1} agents available`}</span>
            </div>
            <label className="sr-only" htmlFor="agent-jump">Select agent</label>
            <select id="agent-jump" value={visibleAgent} onChange={(event) => navigateToAgent(Number(event.target.value))} className="agent-rail-select" aria-label="Select an available agent">
              {agentStages.map((agent, index) => <option key={agent.label} value={index} disabled={index > unlockedAgent}>{index + 1}. {agent.label}{index > unlockedAgent ? " · Locked" : ""}</option>)}
            </select>
            <div className="agent-rail-controls">
              <button type="button" onClick={() => scrollAgentRail(-1)} aria-label="Scroll agents left" title="Scroll agents left"><ChevronLeft size={17} /></button>
              <button type="button" onClick={() => scrollAgentRail(1)} aria-label="Scroll agents right" title="Scroll agents right"><ChevronRight size={17} /></button>
            </div>
          </div>
        <nav
          ref={agentRailRef}
          aria-label="Agent workflow progress"
          className="agent-rail overflow-x-auto px-4"
        >
          <ol className="grid min-w-[2100px] items-start py-4" style={{ gridTemplateColumns: `repeat(${agentStages.length}, minmax(120px, 1fr))` }}>
            {agentStages.map((agent, index) => (
              <li
                key={agent.label}
                data-agent-index={index}
                className={`agent-rail-item relative flex flex-col items-center px-1 text-center text-xs font-bold ${index <= unlockedAgent ? "text-[var(--accent)]" : "text-[var(--muted)]"} ${index === visibleAgent && busy ? "agent-rail-item--running" : ""}`}
              >
                <div
                  aria-hidden="true"
                  className={`mb-2 h-10 w-16 border bg-cover bg-center ${index === visibleAgent ? "border-[var(--ink)] ring-2 ring-[var(--ink)]" : "border-[var(--line)]"} ${index > unlockedAgent ? "grayscale opacity-45" : ""}`}
                  style={{ backgroundImage: `url(${agent.image})` }}
                />
                {index > 0 && (
                  <span
                    aria-hidden="true"
                    className={`absolute right-1/2 top-[3.75rem] h-px w-full ${index <= unlockedAgent ? "bg-[var(--accent)]" : "bg-[var(--line-strong)]"}`}
                  />
                )}
                <button
                  type="button"
                  onClick={() => navigateToAgent(index)}
                  disabled={index > unlockedAgent}
                  aria-current={index === visibleAgent ? "step" : undefined}
                  aria-label={`${agent.label}${index > unlockedAgent ? " (locked)" : ""}`}
                  className={`relative z-10 grid size-7 place-items-center border disabled:cursor-not-allowed ${index === visibleAgent ? "border-[var(--ink)] bg-[var(--ink)] text-white" : index <= unlockedAgent ? "border-[var(--accent)] bg-[var(--accent)] text-white" : "border-[var(--line-strong)] bg-white"}`}
                >
                  {index === visibleAgent && busy ? <Loader2 className="animate-spin" size={14} /> : index < unlockedAgent ? <CheckCircle2 size={14} /> : index + 1}
                </button>
                <button
                  type="button"
                  onClick={() => navigateToAgent(index)}
                  disabled={index > unlockedAgent}
                  className={`mt-2 disabled:cursor-not-allowed ${index === visibleAgent ? "underline decoration-2 underline-offset-4" : ""}`}
                >
                  {agent.label}
                </button>
              </li>
            ))}
          </ol>
        </nav>
        </div>
        <nav className="agent-transition-dock mb-8" aria-label="Move between agents">
          <button type="button" onClick={() => navigateToAgent(visibleAgent - 1)} disabled={visibleAgent === 0} className="agent-transition-dock__button" aria-label={visibleAgent > 0 ? `Previous agent: ${agentStages[visibleAgent - 1].label}` : "No previous agent"}>
            <ChevronLeft size={18} />
            <span><small>Previous agent</small>{visibleAgent > 0 ? agentStages[visibleAgent - 1].label : "Start"}</span>
          </button>
          <div className="agent-transition-dock__current" aria-live="polite">
            <div className="agent-transition-dock__identity">
              <small>Current · {visibleAgent + 1} of {agentStages.length}</small>
              <strong>{currentAgent.label}</strong>
            </div>
            {currentJob ? (
              <button type="button" onClick={currentJob.action} disabled={currentJob.disabled} className="agent-transition-dock__run">
                {busy ? <Loader2 className="animate-spin" size={14} /> : <Bot size={14} />}
                {currentJob.label}
              </button>
            ) : (
              <span className="agent-transition-dock__complete"><CheckCircle2 size={14} /> Step complete</span>
            )}
          </div>
          <button type="button" onClick={() => navigateToAgent(visibleAgent + 1)} disabled={visibleAgent >= unlockedAgent} className="agent-transition-dock__button agent-transition-dock__button--next" aria-label={visibleAgent < unlockedAgent ? `Next agent: ${agentStages[visibleAgent + 1].label}` : "Next agent is locked"}>
            <span><small>{visibleAgent < unlockedAgent ? "Next agent" : "Next step"}</small>{visibleAgent < unlockedAgent ? agentStages[visibleAgent + 1].label : "Complete current job"}</span>
            {visibleAgent < unlockedAgent ? <ChevronRight size={18} /> : <LockKeyhole size={16} />}
          </button>
        </nav>
        <div className="grid min-w-0 gap-7 lg:grid-cols-[minmax(0,1fr)_360px]">
          <section key={visibleAgent} id={`workflow-stage-${visibleStage}`} className={`agent-view-transition agent-view-${transitionDirection} min-w-0 scroll-mt-6 border border-[var(--line)] bg-white p-5 sm:p-7`}>
            <div className="mb-6 flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center bg-[var(--soft)] text-[var(--accent)]">
                <Plus size={20} />
              </span>
              <div>
                <h2 className="font-display text-xl font-semibold">
                  {visibleAgent >= 4 && visibleAgent <= 7
                    ? `${agentStages[visibleAgent].label} workspace`
                    : stageHeadings[visibleStage]}
                </h2>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  {visibleAgent >= 4 && visibleAgent <= 7
                    ? agentStages[visibleAgent].description
                    : stageDescriptions[visibleStage]}
                </p>
              </div>
            </div>
            {latestAgentProposal && (
              <section id="agent-review-proposal" className="agent-page-enter mb-5 border border-[var(--line-strong)] bg-[var(--soft)] p-4" aria-label={`${currentAgent.label} review proposal`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-bold uppercase text-[var(--accent)]">Latest agent review</span>
                    <h3 className="mt-1 font-display text-lg font-semibold">Proposed update from {currentAgent.label}</h3>
                  </div>
                  <span className="bg-amber-100 px-2 py-1 text-xs font-bold text-amber-900">Artifacts unchanged</span>
                </div>
                <p className="mt-3 whitespace-pre-wrap border-l-2 border-[var(--accent)] pl-3 text-sm leading-6 text-[var(--muted)]">{latestAgentProposal.content}</p>
                <p className="mt-3 text-xs font-semibold text-[var(--ink)]">This proposal updates the current view for review. It does not alter generated artifacts until a governed regeneration action is implemented and explicitly confirmed.</p>
              </section>
            )}
            {visibleAgent === 1 && documents.length > 0 ? (
              <div id="workflow-analysis" className="agent-page-enter grid min-w-0 scroll-mt-6 gap-5">
                <div className="min-w-0 border border-[var(--line)] bg-[var(--soft)] p-5">
                  <span className="text-xs font-bold uppercase text-[var(--accent)]">Document analysis</span>
                  <h3 className="mt-1 font-display text-xl font-semibold">Extracted evidence chunks</h3>
                  <p className="mt-2 text-sm text-[var(--muted)]">Documents are split into bounded text chunks with page and section provenance. These chunks feed requirement extraction directly.</p>
                  <div className="mt-4 grid min-w-0 gap-2 sm:grid-cols-2">
                    {documents.map((item) => (
                      <button type="button" key={item.id} onClick={() => inspectDocumentChunks(item)} disabled={item.status !== "processed" || busy} className={`flex min-w-0 items-center justify-between gap-3 border p-3 text-left text-xs disabled:opacity-50 ${selectedChunkDocument?.id === item.id ? "border-[var(--accent)] bg-white" : "border-[var(--line)] bg-white"}`}>
                        <span className="min-w-0 truncate font-semibold">{item.original_name}</span>
                        <span className="shrink-0 capitalize text-[var(--muted)]">{item.status}</span>
                      </button>
                    ))}
                  </div>
                  {documents.some((item) => item.status !== "processed") && (
                    <p className="mt-4 text-xs text-[var(--muted)]">
                      Analyze all uploaded documents before clarification so every source can contribute evidence.
                    </p>
                  )}
                  <p className={`mt-3 border-l-2 bg-white p-3 text-sm font-semibold ${documents.every((item) => item.status === "processed") ? "border-[var(--success)]" : "border-[var(--accent)]"}`}>
                    {documents.every((item) => item.status === "processed") ? "Document evidence ready" : "Document analysis ready"}
                  </p>
                </div>
                <div className="min-w-0 border border-[var(--line)] bg-white p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <span className="text-xs font-bold uppercase text-[var(--accent)]">Chunk and embedding inspector</span>
                      <h3 className="mt-1 font-display text-lg font-semibold">{selectedChunkDocument?.original_name ?? "Select a processed document"}</h3>
                    </div>
                    {selectedChunkDocument && <span className="bg-[var(--soft)] px-2 py-1 text-xs font-bold">{documentChunks.length} chunks</span>}
                  </div>
                  <div className="mt-4 border-l-2 border-[var(--accent)] bg-[var(--soft)] p-3 text-xs leading-5 text-[var(--muted)]">
                    <strong className="text-[var(--ink)]">How it works:</strong> extraction preserves headings and pages, then splits long sections into chunks of at most 4,000 characters. The current workflow sends bounded chunks directly to agents. Semantic embeddings are not generated yet, so no vector similarity is claimed.
                  </div>
                  <div className="mt-4 grid max-h-[560px] gap-3 overflow-y-auto pr-1">
                    {documentChunks.map((chunk) => (
                      <article key={chunk.id} className="border border-[var(--line)] p-4">
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <strong className="text-[var(--accent)]">{chunk.chunk_id}</strong>
                          <span className="bg-[var(--soft)] px-2 py-1">{chunk.token_count} estimated tokens</span>
                          <span className="bg-[var(--soft)] px-2 py-1">{Math.round(chunk.extraction_confidence * 100)}% extraction confidence</span>
                          <span className={chunk.embedding_status === "generated" ? "bg-green-100 px-2 py-1 text-green-800" : "bg-amber-100 px-2 py-1 text-amber-900"}>
                            Embedding: {(chunk.embedding_status ?? "not_generated").replaceAll("_", " ")}
                          </span>
                        </div>
                        <h4 className="mt-3 font-semibold">{chunk.section_heading || "Untitled section"}{chunk.page_number ? ` · page ${chunk.page_number}` : ""}</h4>
                        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[var(--muted)]">{chunk.content}</p>
                        {chunk.embedding_status === "generated" && <p className="mt-2 text-xs text-[var(--muted)]">{chunk.embedding_model} · {chunk.embedding_dimensions} dimensions</p>}
                      </article>
                    ))}
                  </div>
                </div>
              </div>
            ) : visibleStage === 0 && session ? (
              <div className="grid gap-4 border border-[var(--line)] bg-[var(--soft)] p-5">
                <span className="text-xs font-bold uppercase text-[var(--accent)]">Intake complete</span>
                <div>
                  <h3 className="font-display text-xl font-semibold">{project?.name}</h3>
                  <p className="mt-2 text-sm text-[var(--muted)]">
                    {document?.original_name} · {document ? `${(document.size_bytes / 1024).toFixed(1)} KB` : "No document"}
                  </p>
                </div>
              </div>
            ) : visibleStage === 1 && clarificationsComplete && !clarification ? (
              <div className="border border-[var(--line)] bg-[var(--soft)] p-5 sm:p-6">
                <div className="text-center">
                  <CheckCircle2 className="mx-auto mb-4 text-[var(--success)]" size={34} />
                  <strong className="block text-lg">Clarifications complete</strong>
                  <p className="mt-2 text-sm text-[var(--muted)]">Every human choice is retained with its action and timestamp.</p>
                </div>
                <div className="mt-6 grid gap-3 text-left">
                  {clarificationHistory.map((item) => (
                    <article key={item.id} className="border border-[var(--line)] bg-white p-4">
                      <div className="flex flex-wrap items-center gap-2 text-xs font-bold">
                        <span className="text-[var(--accent)]">{item.requirement_id}</span>
                        <span className="bg-[var(--soft)] px-2 py-1 capitalize">{item.severity}</span>
                        <span className="bg-green-100 px-2 py-1 text-green-800 capitalize">{item.action?.replaceAll("_", " ")}</span>
                      </div>
                      <h3 className="mt-3 font-semibold">{item.question}</h3>
                      <p className="mt-2 border-l-2 border-[var(--success)] pl-3 text-sm"><strong>Chosen answer:</strong> {item.answer}</p>
                      {item.answered_at && <p className="mt-2 text-xs text-[var(--muted)]">Saved {new Date(item.answered_at).toLocaleString()}</p>}
                    </article>
                  ))}
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
                  multiple
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
                      : "Choose architecture documents"}
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
              <div id="workflow-agent-page" key={visibleAgent} className="agent-page-enter scroll-mt-6 grid gap-4">
                {visibleAgent === 3 && (
                  <>
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
                    <span className="text-sm font-bold text-[var(--accent)]">Ready to decompose</span>
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
                  </>
                )}
                {visibleAgent === 4 && decompositions.length > 0 && (
                  <section className="scroll-mt-6">
                    <div className="mb-4 flex items-center justify-between gap-4">
                      <div>
                        <span className="text-xs font-bold uppercase text-[var(--accent)]">Decomposition agent</span>
                        <h3 className="mt-1 font-display text-xl font-semibold">Delivery components</h3>
                      </div>
                      {backlog ? (
                        <span className="text-sm font-bold text-[var(--success)]">{backlog.epics.length + backlog.stories.length + backlog.tasks.length} backlog items ready</span>
                      ) : (
                        <span className="text-sm font-bold text-[var(--accent)]">Ready to build</span>
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
                {visibleAgent >= 5 && visibleAgent <= 16 && backlog && (
                  <section className="scroll-mt-6">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <span className="text-xs font-bold uppercase text-[var(--accent)]">{agentStages[visibleAgent].label} agent</span>
                        <h3 className="mt-1 font-display text-xl font-semibold">
                          {visibleAgent === 5 && "Epic, story, and task hierarchy"}
                          {visibleAgent === 6 && "Business value and acceptance criteria"}
                          {visibleAgent === 7 && "Story points and task-hour estimates"}
                          {visibleAgent === 8 && "Dependency map and delivery risks"}
                          {visibleAgent >= 9 && agentStages[visibleAgent].description}
                        </h3>
                      </div>
                      {visibleAgent === 5 ? (
                        <span className="text-sm font-bold text-[var(--success)]">Hierarchy ready</span>
                      ) : visibleAgent === 6 && enriched ? (
                        <span className="text-sm font-bold text-[var(--success)]">Enrichment complete</span>
                      ) : visibleAgent === 6 ? (
                        <span className="text-sm font-bold text-[var(--accent)]">Ready to enrich</span>
                      ) : visibleAgent === 7 && estimated ? (
                        <span className="text-sm font-bold text-[var(--success)]">Estimates ready</span>
                      ) : visibleAgent === 7 ? (
                        <span className="text-sm font-bold text-[var(--accent)]">Ready to estimate</span>
                      ) : dependencies !== null ? (
                        <span className={`text-sm font-bold ${estimationBrief ? "text-[var(--success)]" : "text-[var(--accent)]"}`}>{estimationBrief ? "Dependencies and Epic order reviewed" : "Epic order review required"}</span>
                      ) : (
                        <span className="text-sm font-bold text-[var(--accent)]">Ready to analyze</span>
                      )}
                    </div>
                    {visibleAgent === 8 && dependencies !== null && (
                      <form onSubmit={saveEstimationBrief} className="mt-5 border border-[var(--line-strong)] bg-[var(--soft)] p-5">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <span className="text-xs font-bold uppercase text-[var(--accent)]">Dependency sequencing decision</span>
                            <h4 className="mt-1 font-display text-lg font-semibold">Parallel work and Epic order</h4>
                            <p className="mt-1 text-sm text-[var(--muted)]">Review dependency-safe candidates, then set the preferred Epic delivery order.</p>
                          </div>
                          {estimationBrief && <span className="bg-green-100 px-2 py-1 text-xs font-bold text-green-800">Answers recorded</span>}
                        </div>
                        <label className="mt-4 grid gap-2 text-sm font-semibold">Decision owner<input required value={estimationDraft.answered_by} onChange={(event) => setEstimationDraft((current) => ({ ...current, answered_by: event.target.value }))} className="h-10 border border-[var(--line-strong)] bg-white px-3 font-normal outline-none focus:border-[var(--accent)]" /></label>
                        <section className="mt-5 border-t border-[var(--line)] pt-4">
                          <h5 className="text-sm font-bold">Candidate parallel Epic groups</h5>
                          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{estimationOptions.parallelism_note}</p>
                          <div className="mt-3 grid gap-2 md:grid-cols-2">
                            {estimationOptions.parallel_groups.map((group, index) => (
                              <div key={group.join("-")} className="border border-[var(--line)] bg-white p-3"><span className="text-[10px] font-bold uppercase text-[var(--accent)]">Parallel group {index + 1}</span><div className="mt-2 flex flex-wrap gap-2">{group.map((epicId) => <span key={epicId} className="bg-[var(--soft)] px-2 py-1 text-xs font-bold">{epicId}</span>)}</div></div>
                            ))}
                          </div>
                        </section>
                        <section className="mt-5 border-t border-[var(--line)] pt-4">
                          <h5 className="text-sm font-bold">Preferred Epic delivery order</h5>
                          <div className="mt-3 grid gap-2">
                            {estimationDraft.ranked_epic_ids.map((epicId, index) => {
                              const epic = estimationOptions.epics.find((item) => item.stable_id === epicId);
                              if (!epic) return null;
                              return <div key={epicId} className="grid grid-cols-[32px_minmax(0,1fr)_72px] items-center gap-3 border border-[var(--line)] bg-white p-3">
                                <span className="grid size-8 place-items-center bg-[var(--ink)] text-xs font-bold text-white">{index + 1}</span>
                                <div className="min-w-0"><strong className="block text-sm">{epic.stable_id} · {epic.title}</strong><span className="text-xs text-[var(--muted)]">{epic.architecture_layer} · {epic.business_value}</span></div>
                                <div className="flex justify-end gap-1"><button type="button" onClick={() => moveRankedEpic(index, -1)} disabled={index === 0} className="grid size-8 place-items-center border border-[var(--line)] disabled:opacity-30" aria-label={`Move ${epic.stable_id} up`}><ChevronUp size={15} /></button><button type="button" onClick={() => moveRankedEpic(index, 1)} disabled={index === estimationDraft.ranked_epic_ids.length - 1} className="grid size-8 place-items-center border border-[var(--line)] disabled:opacity-30" aria-label={`Move ${epic.stable_id} down`}><ChevronDown size={15} /></button></div>
                              </div>;
                            })}
                          </div>
                        </section>
                        <label className="mt-4 grid gap-2 text-sm font-semibold">Why is this the correct business priority order?<textarea required value={estimationDraft.priority_rationale} onChange={(event) => setEstimationDraft((current) => ({ ...current, priority_rationale: event.target.value }))} maxLength={4000} className="min-h-24 resize-y border border-[var(--line-strong)] bg-white p-3 font-normal outline-none focus:border-[var(--accent)]" /></label>
                        <button type="submit" disabled={estimationBriefBusy} className="mt-4 flex h-10 items-center gap-2 bg-[var(--ink)] px-4 text-sm font-bold text-white disabled:opacity-50">
                          {estimationBriefBusy ? <Loader2 className="animate-spin" size={16} /> : <CheckCircle2 size={16} />}
                          {estimationBriefBusy ? "Saving order..." : estimationBrief ? "Update Epic order" : "Save Epic order"}
                        </button>
                      </form>
                    )}
                    {visibleAgent >= 5 && visibleAgent <= 7 && <div className="mt-4 grid gap-4">
                      {backlog.epics.map((epic) => (
                        <article key={epic.id} className="border-l-4 border-[var(--accent)] bg-white p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <strong className="text-xs text-[var(--accent)]">{epic.stable_id} · EPIC</strong>
                              <h4 className="mt-1 font-display text-lg font-semibold">{epic.title}</h4>
                              <p className="mt-1 text-xs font-semibold text-[var(--muted)]">Architecture layer: {epic.architecture_layer || "Legacy / unspecified"}</p>
                              {visibleAgent >= 6 && <p className="mt-1 text-sm text-[var(--muted)]">{epic.business_value}</p>}
                              {visibleAgent >= 6 && <span className="mt-2 inline-block bg-[var(--soft)] px-2 py-1 text-xs font-semibold">{epic.priority}</span>}
                            </div>
                            <Traceability apiUrl={API_URL} itemId={epic.id} itemType="epic" itemLabel={`${epic.stable_id}: ${epic.title}`} sourceCount={epic.source_references.length} />
                          </div>
                          {backlog.features.filter((feature) => feature.epic_stable_id === epic.stable_id).length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {backlog.features.filter((feature) => feature.epic_stable_id === epic.stable_id).map((feature) => (
                                <span key={feature.id} className="border border-[var(--line)] bg-white px-2 py-1 text-xs font-semibold">{feature.stable_id} · {feature.title}</span>
                              ))}
                            </div>
                          )}
                          <div className="mt-4 grid gap-3 pl-3">
                            {backlog.stories.filter((story) => story.epic_stable_id === epic.stable_id).map((story) => (
                              <div key={story.id} className="border-l-2 border-[var(--line)] bg-[var(--soft)] p-3">
                                <div className="flex items-start justify-between gap-3">
                                  <div>
                                    <strong className="text-xs text-[var(--accent)]">{story.feature_stable_id} → {story.stable_id} · STORY</strong>
                                    <h5 className="mt-1 font-semibold">{story.title}</h5>
                                    <p className="mt-1 text-sm text-[var(--muted)]">{story.user_story}</p>
                                    {visibleAgent >= 7 && story.story_points !== null && (
                                      <p className="mt-2 text-xs font-semibold">{story.story_points} points · {story.estimation_rationale}</p>
                                    )}
                                    {visibleAgent >= 6 && story.acceptance_criteria.length > 0 && (
                                      <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-[var(--muted)]">
                                        {story.acceptance_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}
                                      </ul>
                                    )}
                                    {story.definition_of_done?.length > 0 && <p className="mt-2 text-xs text-[var(--muted)]"><strong>DoD:</strong> {story.definition_of_done.join(" · ")}</p>}
                                  </div>
                                  <Traceability apiUrl={API_URL} itemId={story.id} itemType="story" itemLabel={`${story.stable_id}: ${story.title}`} sourceCount={story.source_references.length} />
                                </div>
                                <div className="mt-3 grid gap-2 pl-3">
                                  {backlog.tasks.filter((task) => task.story_stable_id === story.stable_id).map((task) => (
                                    <div key={task.id} className="flex items-start justify-between gap-3 border-l border-[var(--line)] bg-white p-3">
                                      <div>
                                        <strong className="text-xs text-[var(--accent)]">{task.stable_id} · {task.work_category?.toUpperCase()} · {task.task_type.toUpperCase()}</strong>
                                        <p className="mt-1 text-sm font-semibold">{task.title}</p>
                                        <p className="mt-1 text-xs text-[var(--muted)]"><strong>Sources:</strong> {task.source_references.join("; ")}</p>
                                        {task.acceptance_criteria?.length > 0 && <p className="mt-1 text-xs text-[var(--muted)]"><strong>Acceptance:</strong> {task.acceptance_criteria.join(" · ")}</p>}
                                        {task.definition_of_done?.length > 0 && <p className="mt-1 text-xs text-[var(--muted)]"><strong>DoD:</strong> {task.definition_of_done.join(" · ")}</p>}
                                        {visibleAgent >= 7 && task.estimated_hours !== null && (
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
                    </div>}
                    {dependencies !== null && (
                      <div className="mt-4 border border-[var(--line)] bg-[var(--soft)] p-4">
                        {visibleAgent === 8 && <><strong className="text-sm">Dependency analysis</strong>
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
                        )}</>}
                        <div id="workflow-content-4-plan" className="scroll-mt-6 mt-4 border-t border-[var(--line)] pt-4">
                          {visibleAgent === 9 && <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <strong className="text-sm">Planning data</strong>
                              <p className="mt-1 text-xs text-[var(--muted)]">Upload the Teams, TeamMembers, Sprints, Holidays, and optional Leaves workbook.</p>
                              <a href={`${API_URL}/planning-data/template`} download className="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-[var(--accent)] underline-offset-4 hover:underline">
                                <Download size={14} /> Download editable template with sample entries
                              </a>
                            </div>
                            {planningReady ? (
                              assignments.length > 0 ? (
                                <span className="text-sm font-bold text-[var(--success)]">Assignments proposed</span>
                              ) : (
                                <span className="text-sm font-bold text-[var(--accent)]">Ready for assignment</span>
                              )
                            ) : (
                              <><span className="text-sm font-bold text-[var(--accent)]">Planning workbook required</span><input id="planning-data-upload" type="file" accept=".xlsx" onChange={uploadPlanningData} disabled={busy} className="sr-only" /></>
                            )}
                          </div>}
                          {visibleAgent === 9 && planningIssues.length > 0 && (
                            <div className="mt-3 grid gap-2">
                              {planningIssues.map((issue, index) => (
                                <p key={`${issue.sheet}-${issue.row}-${issue.field}-${index}`} className={`border-l-2 px-3 py-2 text-xs ${issue.blocking ? "border-red-500 bg-red-50 text-red-900" : "border-amber-500 bg-amber-50 text-amber-900"}`}>
                                  {issue.sheet}{issue.row ? ` row ${issue.row}` : ""}: {issue.message}
                                </p>
                              ))}
                            </div>
                          )}
                          {visibleAgent === 10 && assignments.length > 0 && (
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
                          {visibleAgent === 11 && sprintScope && (
                            <form onSubmit={saveSprintScopeReview} className="mt-4 border-t border-[var(--line)] pt-4">
                              <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                  <span className="text-xs font-bold uppercase text-[var(--accent)]">Sprint scope review</span>
                                  <h4 className="mt-1 font-display text-lg font-semibold">Approve Tasks for planning</h4>
                                  <p className="mt-1 text-xs leading-5 text-[var(--muted)]">Selected Tasks are approved. Unselected Tasks are explicitly discarded, and Stories with no approved Tasks are excluded from the regenerated Sprint plan.</p>
                                </div>
                                <div className="text-right text-xs font-bold">
                                  <span className="text-[var(--success)]">{sprintScopeTaskIds.length} approved</span>
                                  <span className="mx-2 text-[var(--line-strong)]">/</span>
                                  <span className="text-red-700">{sprintScope.stories.flatMap((story) => story.tasks).length - sprintScopeTaskIds.length} discarded</span>
                                </div>
                              </div>
                              <div className="mt-3 flex flex-wrap gap-2">
                                <button type="button" onClick={() => setSprintScopeTaskIds(sprintScope.stories.flatMap((story) => story.tasks.map((task) => task.stable_id)))} className="h-8 border border-[var(--line-strong)] bg-white px-3 text-xs font-bold">Select all</button>
                                <button type="button" onClick={() => setSprintScopeTaskIds([])} className="h-8 border border-[var(--line-strong)] bg-white px-3 text-xs font-bold">Clear all</button>
                              </div>
                              <div className="mt-3 grid max-h-[560px] gap-3 overflow-y-auto pr-1">
                                {sprintScope.stories.map((story) => {
                                  const taskIds = story.tasks.map((task) => task.stable_id);
                                  const selectedCount = taskIds.filter((id) => sprintScopeTaskIds.includes(id)).length;
                                  return <article key={story.stable_id} className="border border-[var(--line)] bg-white p-4">
                                    <div className="flex flex-wrap items-start justify-between gap-3">
                                      <div><strong className="text-sm">{story.stable_id} · {story.title}</strong><p className="mt-1 text-xs text-[var(--muted)]">{story.story_points} points · {story.priority}</p></div>
                                      <label className="flex items-center gap-2 text-xs font-bold"><input type="checkbox" checked={selectedCount === taskIds.length && taskIds.length > 0} onChange={(event) => setSprintScopeTaskIds((current) => event.target.checked ? Array.from(new Set([...current, ...taskIds])) : current.filter((id) => !taskIds.includes(id)))} /> Select Story Tasks</label>
                                    </div>
                                    <div className="mt-3 grid gap-2">
                                      {story.tasks.map((task) => (
                                        <label key={task.stable_id} className={`grid grid-cols-[20px_minmax(0,1fr)_auto] items-start gap-2 border p-3 text-xs ${sprintScopeTaskIds.includes(task.stable_id) ? "border-green-300 bg-green-50" : "border-red-200 bg-red-50"}`}>
                                          <input type="checkbox" checked={sprintScopeTaskIds.includes(task.stable_id)} onChange={(event) => setSprintScopeTaskIds((current) => event.target.checked ? [...current, task.stable_id] : current.filter((id) => id !== task.stable_id))} />
                                          <span><strong className="block">{task.stable_id} · {task.title}</strong><span className="mt-1 block text-[var(--muted)]">{task.work_category.replaceAll("_", " ")}</span></span>
                                          <span className="font-semibold">{task.estimated_hours ?? "?"}h</span>
                                        </label>
                                      ))}
                                    </div>
                                  </article>;
                                })}
                              </div>
                              <div className="mt-4 grid gap-3 md:grid-cols-2">
                                <label className="grid gap-1 text-xs font-bold">Reviewed by<input required value={sprintScopeReviewer} onChange={(event) => setSprintScopeReviewer(event.target.value)} className="h-10 border border-[var(--line-strong)] bg-white px-3 text-sm font-normal" /></label>
                                <label className="grid gap-1 text-xs font-bold">Scope decision note<input value={sprintScopeNote} onChange={(event) => setSprintScopeNote(event.target.value)} className="h-10 border border-[var(--line-strong)] bg-white px-3 text-sm font-normal" /></label>
                              </div>
                              {sprintPlan.length > 0 && <p className="mt-3 border-l-2 border-amber-500 bg-amber-50 p-3 text-xs text-amber-900">Saving this review replaces the existing proposed Sprint plan. Committed Sprints remain unchanged.</p>}
                              <button type="submit" disabled={busy || sprintScopeTaskIds.length === 0} className="mt-4 flex h-10 items-center gap-2 bg-[var(--ink)] px-4 text-sm font-bold text-white disabled:opacity-50"><CheckCircle2 size={16} /> {sprintScope.reviewed ? "Update approved scope" : "Approve selected scope"}</button>
                            </form>
                          )}
                          {visibleAgent === 11 && sprintPlan.length > 0 && (
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
                          {visibleAgent === 12 && duplicateCandidates.length > 0 && (
                            <div className="mt-4 grid gap-2">
                              {duplicateCandidates.map((candidate) => (
                                <article key={candidate.id} className="border border-[var(--line)] bg-white p-4 text-sm">
                                  <div className="flex flex-wrap items-center justify-between gap-2">
                                    <strong>{candidate.source_stable_id} ↔ {candidate.target_stable_id}</strong>
                                    <span className="bg-amber-100 px-2 py-1 text-xs font-bold text-amber-900">{Math.round(candidate.similarity * 100)}% similar</span>
                                  </div>
                                  <p className="mt-2 text-[var(--muted)]">{candidate.rationale}</p>
                                  <p className="mt-2 text-xs font-bold capitalize text-[var(--accent)]">{candidate.recommendation.replaceAll("_", " ")}</p>
                                </article>
                              ))}
                            </div>
                          )}
                          {visibleAgent === 12 && duplicatesComplete && (
                            <form onSubmit={checkProposedStory} className="mt-4 border-t border-[var(--line)] pt-4">
                              <span className="text-xs font-bold uppercase text-[var(--accent)]">New-story gate</span>
                              <h4 className="mt-1 font-display text-lg font-semibold">Check before creation</h4>
                              <div className="mt-3 grid gap-3 md:grid-cols-2">
                                <input required value={newStoryDraft.title} onChange={(event) => setNewStoryDraft((current) => ({ ...current, title: event.target.value }))} placeholder="Story title" className="h-10 border border-[var(--line)] bg-white px-3 text-sm" />
                                <select value={newStoryDraft.priority} onChange={(event) => setNewStoryDraft((current) => ({ ...current, priority: event.target.value }))} className="h-10 border border-[var(--line)] bg-white px-3 text-sm"><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select>
                                <textarea required value={newStoryDraft.user_story} onChange={(event) => setNewStoryDraft((current) => ({ ...current, user_story: event.target.value }))} placeholder="As a..., I want..., so that..." className="min-h-20 border border-[var(--line)] bg-white p-3 text-sm md:col-span-2" />
                                <textarea required value={newStoryDraft.description} onChange={(event) => setNewStoryDraft((current) => ({ ...current, description: event.target.value }))} placeholder="Description" className="min-h-20 border border-[var(--line)] bg-white p-3 text-sm md:col-span-2" />
                                <select value={newStoryDraft.story_points} onChange={(event) => setNewStoryDraft((current) => ({ ...current, story_points: event.target.value }))} className="h-10 border border-[var(--line)] bg-white px-3 text-sm">{[1, 2, 3, 5, 8, 13].map((point) => <option key={point}>{point}</option>)}</select>
                                <textarea required value={newStoryDraft.source_references} onChange={(event) => setNewStoryDraft((current) => ({ ...current, source_references: event.target.value }))} placeholder="Source references, one per line" className="min-h-20 border border-[var(--line)] bg-white p-3 text-sm" />
                                <textarea required value={newStoryDraft.acceptance_criteria} onChange={(event) => setNewStoryDraft((current) => ({ ...current, acceptance_criteria: event.target.value }))} placeholder="Acceptance criteria, one per line" className="min-h-24 border border-[var(--line)] bg-white p-3 text-sm" />
                                <textarea required value={newStoryDraft.definition_of_done} onChange={(event) => setNewStoryDraft((current) => ({ ...current, definition_of_done: event.target.value }))} placeholder="Definition of Done, one per line" className="min-h-24 border border-[var(--line)] bg-white p-3 text-sm" />
                              </div>
                              <button type="submit" disabled={busy} className="mt-3 flex h-10 items-center gap-2 bg-[var(--ink)] px-4 text-sm font-bold text-white disabled:opacity-50"><ShieldCheck size={16} /> Check semantic duplicates</button>
                              {newStoryCheck && (
                                <div className="mt-3 border border-[var(--line-strong)] bg-white p-4 text-sm">
                                  <strong className="capitalize">{newStoryCheck.classification}</strong>
                                  <p className="mt-1 text-[var(--muted)]">{newStoryCheck.rationale}</p>
                                  {newStoryCheck.equivalent_story_id && <p className="mt-2 font-semibold">Equivalent ticket: {newStoryCheck.equivalent_story_id}</p>}
                                  {newStoryCheck.clarifying_questions.map((question) => <p key={question} className="mt-2 text-amber-900">{question}</p>)}
                                  {newStoryCheck.classification === "new" && newStoryCheck.status !== "created" && <button type="button" onClick={confirmNewStory} className="mt-3 h-9 bg-[var(--accent)] px-3 text-xs font-bold text-white">Confirm story creation</button>}
                                  {newStoryCheck.status === "created" && <p className="mt-2 font-bold text-[var(--success)]">Story created. Sprint plan unchanged.</p>}
                                </div>
                              )}
                            </form>
                          )}
                          {visibleAgent === 13 && qualityClarifications.some((item) => item.status === "pending") && (
                            <div className="mt-4 border-t border-[var(--line)] pt-4">
                              <span className="text-xs font-bold uppercase text-[var(--accent)]">85% readiness gate</span>
                              <h4 className="mt-1 font-display text-lg font-semibold">Human clarification required</h4>
                              <div className="mt-3 grid gap-3">
                                {qualityClarifications.filter((item) => item.status === "pending").map((item) => (
                                  <article key={item.id} className="border border-amber-300 bg-amber-50 p-4">
                                    <strong className="text-sm">{item.item_id} · {item.item_type}</strong>
                                    <p className="mt-1 text-xs text-amber-900">{item.question}</p>
                                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                                      {item.missing_fields.map((check) => {
                                        const field = check === "source_traceable" ? "source_references" : check === "priority_set" ? "priority" : check === "estimated" ? item.item_type === "story" ? "story_points" : "estimated_hours" : check.replace(/_present$/, "");
                                        const multiline = ["source_references", "acceptance_criteria", "definition_of_done"].includes(field);
                                        return <label key={field} className="grid gap-1 text-xs font-bold capitalize">{field.replaceAll("_", " ")}{multiline ? <textarea value={qualityAnswerDrafts[item.id]?.[field] ?? ""} onChange={(event) => setQualityAnswerDrafts((current) => ({ ...current, [item.id]: { ...current[item.id], [field]: event.target.value } }))} placeholder="One value per line" className="min-h-20 border border-amber-300 bg-white p-2 font-normal" /> : <input value={qualityAnswerDrafts[item.id]?.[field] ?? ""} onChange={(event) => setQualityAnswerDrafts((current) => ({ ...current, [item.id]: { ...current[item.id], [field]: event.target.value } }))} className="h-9 border border-amber-300 bg-white px-2 font-normal" />}</label>;
                                      })}
                                    </div>
                                    <button type="button" onClick={() => answerQualityClarification(item)} disabled={busy} className="mt-3 h-9 bg-[var(--ink)] px-3 text-xs font-bold text-white disabled:opacity-50">Record answer</button>
                                  </article>
                                ))}
                              </div>
                            </div>
                          )}
                          {visibleAgent === 13 && qualityResults.length > 0 && (
                            <div className="mt-4 border-t border-[var(--line)] pt-4">
                              <strong className="text-sm">85% readiness results</strong>
                              <p className="mt-1 text-xs text-[var(--muted)]">{qualityResults.filter((item) => item.passed).length}/{qualityResults.length} backlog items pass the quality gate.</p>
                              <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                {qualityResults.map((result) => (
                                  <div key={result.id} className={`border-l-2 bg-white p-3 text-xs ${result.passed ? "border-green-500" : "border-red-500"}`}>
                                    <strong>{result.item_id} · {result.score}%</strong>
                                    <span className="mt-1 block capitalize text-[var(--muted)]">{result.item_type}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          {visibleAgent >= 14 && qualityResults.length > 0 && boardHealth && (
                            <div className="mt-4 border-t border-[var(--line)] pt-4">
                              <div className="flex flex-wrap items-center justify-between gap-3">
                                <div>
                                  <strong className="text-sm">Board health: {boardHealth.score}/100 · {boardHealth.risk_level} risk</strong>
                                  <p className="mt-1 text-xs text-[var(--muted)]">{qualityResults.filter((item) => item.passed).length}/{qualityResults.length} items pass quality · {duplicateCandidates.length} duplicate candidates</p>
                                </div>
                                <span className="bg-amber-100 px-2 py-1 text-xs font-bold text-amber-900">Human approval required</span>
                              </div>
                              {boardHealth.metrics.quality_score !== undefined && (
                                <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-5">
                                  {[
                                    ["Quality", boardHealth.metrics.quality_score, 35],
                                    ["Duplicate readiness", boardHealth.metrics.duplicate_readiness_score, 10],
                                    ["Dependency readiness", boardHealth.metrics.dependency_readiness_score, 15],
                                    ["Delivery feasibility", boardHealth.metrics.delivery_feasibility_score, 30],
                                    ["Ownership coverage", boardHealth.metrics.ownership_coverage_score, 10],
                                  ].map(([label, value, maximum]) => (
                                    <div key={String(label)} className="border-l-2 border-[var(--accent)] pl-2">
                                      <span className="block text-[var(--muted)]">{label}</span>
                                      <strong>{Number(value).toFixed(1)} / {maximum}</strong>
                                    </div>
                                  ))}
                                </div>
                              )}
                              {boardHealth.issues.map((issue) => <p key={issue} className="mt-2 text-xs text-amber-900">{issue}</p>)}
                              {!publishedExport && (
                                <div className="mt-4 grid gap-3 md:grid-cols-2">
                                  <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="Reviewer name" className="h-10 border border-[var(--line)] bg-white px-3 text-sm" />
                                  <input value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} placeholder="Review note" className="h-10 border border-[var(--line)] bg-white px-3 text-sm" />
                                  <div className="flex flex-wrap gap-2 md:col-span-2">
                                    <button type="button" onClick={() => submitApproval("approve")} disabled={busy || !reviewer.trim()} className="h-10 bg-[var(--success)] px-4 text-sm font-bold text-white disabled:opacity-50">Approve</button>
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
              <div id="workflow-analysis" className="scroll-mt-6 flex min-h-64 items-center justify-center border border-[var(--line)] bg-[var(--soft)] p-8 text-center">
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
                  <p className="mt-4 text-sm font-bold text-[var(--accent)]">Requirement generation ready</p>
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
                      ? `${documents.length} architecture document${documents.length === 1 ? "" : "s"} extracted for clarification.`
                      : `${documents.length} architecture document${documents.length === 1 ? "" : "s"} ready for analysis.`}
                  </p>
                  <div className="mx-auto mt-4 grid max-w-lg gap-2 text-left">
                    {documents.map((item) => (
                      <div key={item.id} className="flex items-center justify-between gap-3 border border-[var(--line)] bg-white px-3 py-2 text-xs">
                        <span className="truncate font-semibold">{item.original_name}</span>
                        <span className="shrink-0 capitalize text-[var(--muted)]">{item.status}</span>
                      </div>
                    ))}
                  </div>
                  {!analysisJob ? (
                    <div className="mt-6 flex flex-wrap justify-center gap-2">
                      <label className="flex h-10 cursor-pointer items-center gap-2 border border-[var(--line-strong)] bg-white px-4 text-sm font-bold">
                        <Plus size={16} /> Add architectures
                        <input className="sr-only" type="file" multiple accept=".pdf,.docx,.xlsx,.txt,.md,.csv" onChange={uploadDocument} disabled={busy} />
                      </label>
                    </div>
                  ) : (
                    <p className="mt-4 text-sm font-bold text-[var(--success)]">Document analysis complete</p>
                  )}
                </div>
              </div>
            )}
          </section>
          <aside className="min-w-0 self-start overflow-hidden border border-[var(--line-strong)] bg-white lg:sticky lg:top-6">
            <div className="bg-[var(--ink)] p-5 text-white">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <span className="text-[10px] font-bold uppercase text-[var(--accent-light)]">Control plane</span>
                  <h2 className="mt-1 font-display text-xl font-semibold">{project?.name ?? "New project"}</h2>
                </div>
                <span className="border border-white/20 px-2 py-1 text-xs font-bold">{workflowProgress}%</span>
              </div>
              <div className="mt-4 h-1.5 overflow-hidden bg-white/15" aria-label={`${workflowProgress}% workflow complete`}>
                <div className="h-full bg-[var(--accent-light)] transition-[width] duration-500" style={{ width: `${workflowProgress}%` }} />
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-white/65">
                <span>{unlockedAgent + 1} of {agentStages.length} agents reached</span>
                <span>SQLite-backed</span>
              </div>
            </div>

            <div className="border-b border-[var(--line)] bg-[var(--soft)] p-5">
              <span className="text-[10px] font-bold uppercase text-[var(--accent)]">Current view</span>
              <div className="mt-2 flex items-start justify-between gap-4">
                <div>
                  <strong className="font-display text-lg">{currentAgent.label}</strong>
                  <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{currentAgent.description}</p>
                </div>
                <span className="grid size-8 shrink-0 place-items-center bg-[var(--ink)] text-xs font-bold text-white">{visibleAgent + 1}</span>
              </div>
            </div>

            {session && (
              <div className="border-b border-[var(--line)] p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-bold uppercase text-[var(--accent)]">Review with this agent</span>
                    <h3 className="mt-1 text-sm font-bold">Add context or challenge the result</h3>
                  </div>
                  <Bot size={18} className="shrink-0 text-[var(--accent)]" />
                </div>
                {agentMessages.length > 0 && (
                  <div className="mt-3 grid max-h-52 gap-2 overflow-y-auto border-y border-[var(--line)] py-3">
                    {agentMessages.map((message) => (
                      <div key={message.id} className={`whitespace-pre-wrap p-3 text-xs leading-5 ${message.role === "human" ? "ml-5 bg-[var(--ink)] text-white" : "mr-5 bg-[var(--soft)] text-[var(--ink)]"}`}>
                        <span className={`mb-1 block text-[10px] font-bold uppercase ${message.role === "human" ? "text-white/60" : "text-[var(--accent)]"}`}>{message.role === "human" ? "You" : currentAgent.label}</span>
                        {message.content}
                      </div>
                    ))}
                  </div>
                )}
                <form onSubmit={sendAgentPrompt} className="mt-3">
                  <label className="sr-only" htmlFor="agent-review-prompt">Feedback for {currentAgent.label}</label>
                  <textarea
                    id="agent-review-prompt"
                    value={agentPrompt}
                    onChange={(event) => setAgentPrompt(event.target.value)}
                    maxLength={4000}
                    placeholder={`Tell ${currentAgent.label} what seems wrong or add missing information...`}
                    className="min-h-24 w-full resize-y border border-[var(--line-strong)] p-3 text-sm outline-none focus:border-[var(--accent)]"
                  />
                  <button type="submit" disabled={agentPromptBusy || !agentPrompt.trim()} className="mt-2 flex h-9 w-full items-center justify-center gap-2 bg-[var(--accent)] px-3 text-xs font-bold text-white disabled:opacity-50">
                    {agentPromptBusy ? <Loader2 className="animate-spin" size={14} /> : <Bot size={14} />}
                    {agentPromptBusy ? "Agent reviewing..." : `Ask ${currentAgent.label}`}
                  </button>
                </form>
                <p className="mt-2 text-[11px] leading-4 text-[var(--muted)]">The completed response appears in the current view as a persisted revision proposal. It does not overwrite artifacts, approve work, or publish automatically.</p>
              </div>
            )}

            <div className="grid gap-0 px-5">
              <Status
                icon={<FileText size={17} />}
                label="Source evidence"
                value={
                  analysisJob
                    ? "Extracted"
                    : documents.length > 0
                      ? `${documents.length} document${documents.length === 1 ? "" : "s"}`
                      : "Awaiting upload"
                }
                        tone={analysisJob ? "complete" : documents.length > 0 ? "active" : "pending"}
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
                        tone={clarificationsComplete ? "complete" : clarification ? "active" : "pending"}
              />
              <Status
                icon={<FileText size={17} />}
                label="Requirements"
                value={
                  requirements.length
                    ? `${requirements.length} generated`
                    : "Not generated"
                }
                tone={requirements.length > 0 ? "complete" : "pending"}
              />
              <Status
                icon={<GitBranch size={17} />}
                label="Backlog hierarchy"
                value={backlog ? `${backlog.epics.length} epics · ${backlog.stories.length} stories · ${backlog.tasks.length} tasks` : "Not generated"}
                tone={backlog ? "complete" : "pending"}
              />
              <Status
                icon={<GitBranch size={17} />}
                label="Dependency integrity"
                value={dependencies !== null ? `${dependencies.length} relationship${dependencies.length === 1 ? "" : "s"} analyzed` : "Not analyzed"}
                tone={dependencies !== null ? "complete" : "pending"}
              />
              <Status
                icon={<ShieldCheck size={17} />}
                label="Publishing gate"
                value={publishedExport ? "Workbook published" : approved ? "Approved for publishing" : boardHealth ? "Awaiting named approval" : "Locked until review"}
                tone={publishedExport ? "complete" : approved || boardHealth ? "active" : "pending"}
              />
            </div>

            <div className="border-t border-[var(--line)] p-5">
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-xs font-bold"><Coins size={15} className="text-[var(--accent)]" /> LLM usage</span>
                <strong className="text-sm">{llmUsage ? llmUsage.total_tokens.toLocaleString() : "0"}</strong>
              </div>
              <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
                {llmUsage
                  ? `${llmUsage.input_tokens.toLocaleString()} input · ${llmUsage.output_tokens.toLocaleString()} output tokens`
                  : "Usage will appear after an AI agent runs."}
              </p>
              {llmUsage?.remaining_reported && (
                <p className="mt-1 text-xs text-[var(--success)]">{llmUsage.remaining_tokens?.toLocaleString()} provider-window tokens available</p>
              )}
            </div>
            <div className="border-t border-[var(--line)] bg-[var(--soft)] p-5 text-xs leading-5 text-[var(--muted)]">
              <div className="mb-2 flex items-center gap-2 font-bold text-[var(--ink)]"><ShieldCheck size={15} className="text-[var(--success)]" /> Human-governed delivery</div>
              Final exports remain locked until a named reviewer approves the project. API keys never reach this client.
            </div>
          </aside>
        </div>
          </>
        )}
      </main>
    </div>
  );
}

function Status({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: "complete" | "active" | "pending";
}) {
  return (
    <div className="flex gap-3 border-b border-[var(--line)] py-4 last:border-b-0">
      <span className={`mt-0.5 ${tone === "complete" ? "text-[var(--success)]" : tone === "active" ? "text-[var(--accent)]" : "text-[var(--muted)]"}`}>{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-[var(--muted)]">{label}</p>
          <span className={`size-2 shrink-0 ${tone === "complete" ? "bg-[var(--success)]" : tone === "active" ? "bg-[var(--accent)]" : "border border-[var(--line-strong)] bg-white"}`} />
        </div>
        <p className="mt-1 text-sm font-semibold text-[var(--ink)]">{value}</p>
      </div>
    </div>
  );
}
