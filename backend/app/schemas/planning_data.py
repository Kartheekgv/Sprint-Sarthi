from pydantic import BaseModel, ConfigDict, Field


class PlanningIssue(BaseModel):
    sheet: str
    row: int | None = None
    field: str
    message: str
    blocking: bool


class PlanningImportResult(BaseModel):
    project_id: str
    filename: str
    teams_imported: int
    members_imported: int
    sprints_imported: int
    holidays_imported: int
    leaves_imported: int
    requires_clarification: bool
    issues: list[PlanningIssue]


class AssignmentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_stable_id: str = Field(pattern=r"^(STORY|TASK)-\d{3,}$")
    team_member_id: str = Field(min_length=1, max_length=100)
    recommended_hours: float | None = Field(default=None, gt=0, le=200)
    match_score: float = Field(ge=0, le=1)
    reason: str = Field(min_length=10, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class AssignmentBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignments: list[AssignmentDraft] = Field(min_length=1, max_length=1200)


class AssignmentRead(BaseModel):
    id: str
    item_stable_id: str
    team_member_id: str
    team_member_name: str
    role: str
    department: str
    recommended_hours: float | None
    match_score: float
    reason: str
    confidence: float
    provenance: dict[str, object]
    status: str


class AssignmentGenerationResult(BaseModel):
    session_id: str
    session_status: str
    assignments: list[AssignmentRead]