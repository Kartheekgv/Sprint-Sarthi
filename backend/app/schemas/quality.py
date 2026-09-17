from pydantic import BaseModel


class QualityRead(BaseModel):
    id: str
    item_id: str
    item_type: str
    score: int
    passed: bool
    issues: list[str]
    checks: dict[str, bool]


class QualityGenerationResult(BaseModel):
    session_id: str
    session_status: str
    results: list[QualityRead]


class BoardHealthRead(BaseModel):
    id: str
    score: int
    risk_level: str
    metrics: dict[str, int | float]
    issues: list[str]
    status: str


class BoardHealthGenerationResult(BaseModel):
    session_id: str
    session_status: str
    health: BoardHealthRead