from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


RunStatus = Literal["pending", "running", "completed", "failed"]


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    github_repo_url: HttpUrl
    default_branch: str = "main"


class ProjectResponse(BaseModel):
    id: UUID
    owner_id: str
    name: str
    github_repo_url: str
    default_branch: str
    created_at: datetime


class RunCreateRequest(BaseModel):
    github_ref: str | None = None


class RunResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: RunStatus
    github_ref: str
    parser_version: str
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None


class HotspotItem(BaseModel):
    function_name: str
    score: float
    label: str = "kritik uyari"
    rank: int


class DependencyNode(BaseModel):
    id: str
    label: str


class DependencyEdge(BaseModel):
    source: str
    target: str
    relation_type: str


class DependencyGraphResponse(BaseModel):
    nodes: list[DependencyNode]
    edges: list[DependencyEdge]


class TrendPoint(BaseModel):
    run_id: UUID
    created_at: datetime
    value: float


class TrendResponse(BaseModel):
    metric: str
    points: list[TrendPoint]


def make_project_response(owner_id: str, payload: ProjectCreateRequest) -> ProjectResponse:
    return ProjectResponse(
        id=uuid4(),
        owner_id=owner_id,
        name=payload.name,
        github_repo_url=str(payload.github_repo_url),
        default_branch=payload.default_branch,
        created_at=datetime.utcnow(),
    )
