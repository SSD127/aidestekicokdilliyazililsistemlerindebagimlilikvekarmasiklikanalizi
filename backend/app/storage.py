from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.schemas import (
    DependencyEdge,
    DependencyGraphResponse,
    DependencyNode,
    HotspotItem,
    ProjectCreateRequest,
    ProjectResponse,
    RunCreateRequest,
    RunResponse,
    TrendPoint,
    TrendResponse,
    make_project_response,
)


@dataclass
class InMemoryStore:
    projects: dict[UUID, ProjectResponse] = field(default_factory=dict)
    runs_by_project: dict[UUID, list[RunResponse]] = field(default_factory=lambda: defaultdict(list))

    def create_project(self, owner_id: str, payload: ProjectCreateRequest) -> ProjectResponse:
        project = make_project_response(owner_id, payload)
        self.projects[project.id] = project
        return project

    def list_projects(self, owner_id: str) -> list[ProjectResponse]:
        return [project for project in self.projects.values() if project.owner_id == owner_id]

    def create_run(self, project_id: UUID, payload: RunCreateRequest) -> RunResponse:
        run = RunResponse(
            id=uuid4(),
            project_id=project_id,
            status="pending",
            github_ref=payload.github_ref or "main",
            parser_version="tree-sitter:v0",
            started_at=datetime.utcnow(),
        )
        self.runs_by_project[project_id].append(run)
        return run

    def list_runs(self, project_id: UUID) -> list[RunResponse]:
        return self.runs_by_project[project_id]

    def get_run(self, project_id: UUID, run_id: UUID) -> RunResponse | None:
        runs = self.runs_by_project.get(project_id, [])
        for run in runs:
            if run.id == run_id:
                return run
        return None

    def build_hotspots(self, project_id: UUID, run_id: UUID) -> list[HotspotItem]:
        run = self.get_run(project_id, run_id)
        if not run:
            return []
        return [
            HotspotItem(function_name="analyze_project", score=18.0, rank=1),
            HotspotItem(function_name="extract_dependencies", score=14.0, rank=2),
            HotspotItem(function_name="calculate_halstead", score=12.0, rank=3),
            HotspotItem(function_name="calculate_mccabe", score=11.0, rank=4),
            HotspotItem(function_name="parse_files", score=10.0, rank=5),
        ]

    def build_graph(self, project_id: UUID, run_id: UUID) -> DependencyGraphResponse:
        run = self.get_run(project_id, run_id)
        if not run:
            return DependencyGraphResponse(nodes=[], edges=[])

        nodes = [
            DependencyNode(id="app/main.py", label="app/main.py"),
            DependencyNode(id="app/storage.py", label="app/storage.py"),
            DependencyNode(id="app/schemas.py", label="app/schemas.py"),
        ]
        edges = [
            DependencyEdge(source="app/main.py", target="app/storage.py", relation_type="import"),
            DependencyEdge(source="app/main.py", target="app/schemas.py", relation_type="import"),
        ]
        return DependencyGraphResponse(nodes=nodes, edges=edges)

    def build_trend(self, project_id: UUID, metric: str) -> TrendResponse:
        points: list[TrendPoint] = []
        for run in self.runs_by_project.get(project_id, []):
            points.append(
                TrendPoint(
                    run_id=run.id,
                    created_at=run.started_at,
                    value=10.0,
                )
            )
        return TrendResponse(metric=metric, points=points)


store = InMemoryStore()
