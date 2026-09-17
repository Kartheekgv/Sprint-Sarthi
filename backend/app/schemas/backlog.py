from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EpicDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epic_key: str = Field(pattern=r"^E\d+$")
    decomposition_ids: list[str] = Field(min_length=1, max_length=40)
    title: str = Field(min_length=5, max_length=500)
    description: str = Field(min_length=10, max_length=5000)
    business_value: str = Field(min_length=5, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class StoryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    story_key: str = Field(pattern=r"^S\d+$")
    parent_epic_key: str = Field(pattern=r"^E\d+$")
    decomposition_ids: list[str] = Field(min_length=1, max_length=40)
    title: str = Field(min_length=5, max_length=500)
    user_story: str = Field(min_length=10, max_length=2000)
    description: str = Field(min_length=10, max_length=5000)
    confidence: float = Field(ge=0, le=1)


class TaskDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_key: str = Field(pattern=r"^T\d+$")
    parent_story_key: str = Field(pattern=r"^S\d+$")
    decomposition_ids: list[str] = Field(min_length=1, max_length=40)
    title: str = Field(min_length=5, max_length=500)
    description: str = Field(min_length=10, max_length=5000)
    task_type: Literal["implementation", "testing", "documentation", "analysis", "configuration"]
    confidence: float = Field(ge=0, le=1)


class BacklogBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epics: list[EpicDraft] = Field(min_length=1, max_length=30)
    stories: list[StoryDraft] = Field(min_length=1, max_length=100)
    tasks: list[TaskDraft] = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "BacklogBatch":
        epic_keys = [item.epic_key for item in self.epics]
        story_keys = [item.story_key for item in self.stories]
        task_keys = [item.task_key for item in self.tasks]
        if len(epic_keys) != len(set(epic_keys)):
            raise ValueError("Epic keys must be unique")
        if len(story_keys) != len(set(story_keys)):
            raise ValueError("Story keys must be unique")
        if len(task_keys) != len(set(task_keys)):
            raise ValueError("Task keys must be unique")
        if any(item.parent_epic_key not in epic_keys for item in self.stories):
            raise ValueError("Every story must reference an epic in this batch")
        if any(item.parent_story_key not in story_keys for item in self.tasks):
            raise ValueError("Every task must reference a story in this batch")
        if set(epic_keys) != {item.parent_epic_key for item in self.stories}:
            raise ValueError("Every epic must contain at least one story")
        if set(story_keys) != {item.parent_story_key for item in self.tasks}:
            raise ValueError("Every story must contain at least one task")
        return self


class EpicRead(BaseModel):
    id: str
    stable_id: str
    decomposition_ids: list[str]
    requirement_ids: list[str]
    title: str
    description: str
    business_value: str
    priority: str
    source_references: list[str]
    provenance: dict[str, object]
    status: str


class StoryRead(BaseModel):
    id: str
    stable_id: str
    epic_stable_id: str
    decomposition_ids: list[str]
    requirement_ids: list[str]
    title: str
    user_story: str
    description: str
    acceptance_criteria: list[str]
    priority: str
    story_points: int | None
    estimation_rationale: str
    source_references: list[str]
    provenance: dict[str, object]
    status: str


class TaskRead(BaseModel):
    id: str
    stable_id: str
    story_stable_id: str
    decomposition_ids: list[str]
    requirement_ids: list[str]
    title: str
    description: str
    task_type: str
    priority: str
    estimated_hours: float | None
    estimation_rationale: str
    source_references: list[str]
    provenance: dict[str, object]
    status: str


class BacklogGenerationResult(BaseModel):
    session_id: str
    session_status: str
    epics: list[EpicRead]
    stories: list[StoryRead]
    tasks: list[TaskRead]