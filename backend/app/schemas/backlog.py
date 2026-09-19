from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EpicDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epic_key: str = Field(pattern=r"^E\d+$")
    decomposition_ids: list[str] = Field(min_length=1, max_length=40)
    title: str = Field(min_length=5, max_length=500)
    description: str = Field(min_length=10, max_length=5000)
    architecture_layer: str = Field(min_length=2, max_length=200)
    business_value: str = Field(min_length=5, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class FeatureDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_key: str = Field(pattern=r"^F\d+$")
    parent_epic_key: str = Field(pattern=r"^E\d+$")
    decomposition_ids: list[str] = Field(min_length=1, max_length=40)
    title: str = Field(min_length=5, max_length=500)
    description: str = Field(min_length=10, max_length=5000)
    business_value: str = Field(min_length=5, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class StoryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    story_key: str = Field(pattern=r"^S\d+$")
    parent_feature_key: str = Field(pattern=r"^F\d+$")
    decomposition_ids: list[str] = Field(min_length=1, max_length=40)
    title: str = Field(min_length=5, max_length=500)
    user_story: str = Field(min_length=10, max_length=2000)
    description: str = Field(min_length=10, max_length=5000)
    definition_of_done: list[str] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0, le=1)


class TaskDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_key: str = Field(pattern=r"^T\d+$")
    parent_story_key: str = Field(pattern=r"^S\d+$")
    decomposition_ids: list[str] = Field(min_length=1, max_length=40)
    title: str = Field(min_length=5, max_length=500)
    description: str = Field(min_length=10, max_length=5000)
    task_type: Literal["implementation", "testing", "documentation", "analysis", "configuration"]
    work_category: Literal["functional", "qa", "enabler", "infrastructure", "security", "compliance", "release"]
    acceptance_criteria: list[str] = Field(min_length=1, max_length=12)
    definition_of_done: list[str] = Field(min_length=1, max_length=12)
    confidence: float = Field(ge=0, le=1)


class BacklogBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epics: list[EpicDraft] = Field(min_length=1, max_length=100)
    features: list[FeatureDraft] = Field(min_length=1, max_length=300)
    stories: list[StoryDraft] = Field(min_length=1, max_length=300)
    tasks: list[TaskDraft] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "BacklogBatch":
        epic_keys = [item.epic_key for item in self.epics]
        feature_keys = [item.feature_key for item in self.features]
        story_keys = [item.story_key for item in self.stories]
        task_keys = [item.task_key for item in self.tasks]
        if len(epic_keys) != len(set(epic_keys)):
            raise ValueError("Epic keys must be unique")
        if len(story_keys) != len(set(story_keys)):
            raise ValueError("Story keys must be unique")
        if len(task_keys) != len(set(task_keys)):
            raise ValueError("Task keys must be unique")
        if len(feature_keys) != len(set(feature_keys)):
            raise ValueError("Feature keys must be unique")
        if any(item.parent_epic_key not in epic_keys for item in self.features):
            raise ValueError("Every feature must reference an epic in this batch")
        if any(item.parent_feature_key not in feature_keys for item in self.stories):
            raise ValueError("Every story must reference a feature in this batch")
        if any(item.parent_story_key not in story_keys for item in self.tasks):
            raise ValueError("Every task must reference a story in this batch")
        if set(epic_keys) != {item.parent_epic_key for item in self.features}:
            raise ValueError("Every epic must contain at least one feature")
        if set(feature_keys) != {item.parent_feature_key for item in self.stories}:
            raise ValueError("Every feature must contain at least one story")
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
    architecture_layer: str
    business_value: str
    priority: str
    source_references: list[str]
    provenance: dict[str, object]
    status: str


class FeatureRead(BaseModel):
    id: str
    stable_id: str
    epic_stable_id: str
    decomposition_ids: list[str]
    requirement_ids: list[str]
    title: str
    description: str
    business_value: str
    source_references: list[str]
    provenance: dict[str, object]
    status: str


class StoryRead(BaseModel):
    id: str
    stable_id: str
    epic_stable_id: str
    feature_stable_id: str
    decomposition_ids: list[str]
    requirement_ids: list[str]
    title: str
    user_story: str
    description: str
    acceptance_criteria: list[str]
    definition_of_done: list[str]
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
    work_category: str
    acceptance_criteria: list[str]
    definition_of_done: list[str]
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
    features: list[FeatureRead]
    stories: list[StoryRead]
    tasks: list[TaskRead]