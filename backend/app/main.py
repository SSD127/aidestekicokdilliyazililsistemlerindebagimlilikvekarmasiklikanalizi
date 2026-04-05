from typing import Literal
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Query, status

from app.config import get_settings
from app.schemas import ProjectCreateRequest, ProjectResponse, RunCreateRequest, RunResponse
from app.storage import store
from app.services.github_pipeline import validate_github_repo_url

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.app_debug)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


def get_current_user_id(x_user_id: str | None) -> str:
    # TODO: Supabase JWT dogrulamasi ile degistir.
    return x_user_id or "local-dev-user"


@app.post("/api/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreateRequest, x_user_id: str | None = Header(default=None)) -> ProjectResponse:
    user_id = get_current_user_id(x_user_id)
    if not validate_github_repo_url(str(payload.github_repo_url)):
        raise HTTPException(status_code=400, detail="Gecerli bir GitHub repo URL giriniz.")
    return store.create_project(owner_id=user_id, payload=payload)


@app.get("/api/projects", response_model=list[ProjectResponse])
def list_projects(x_user_id: str | None = Header(default=None)) -> list[ProjectResponse]:
    user_id = get_current_user_id(x_user_id)
    return store.list_projects(owner_id=user_id)


@app.post("/api/projects/{project_id}/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    project_id: UUID,
    payload: RunCreateRequest,
    x_user_id: str | None = Header(default=None),
) -> RunResponse:
    user_id = get_current_user_id(x_user_id)
    projects = store.list_projects(owner_id=user_id)
    if not any(project.id == project_id for project in projects):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.create_run(project_id=project_id, payload=payload)


@app.get("/api/projects/{project_id}/runs", response_model=list[RunResponse])
def list_runs(project_id: UUID, x_user_id: str | None = Header(default=None)) -> list[RunResponse]:
    user_id = get_current_user_id(x_user_id)
    projects = store.list_projects(owner_id=user_id)
    if not any(project.id == project_id for project in projects):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.list_runs(project_id)


@app.get("/api/projects/{project_id}/runs/{run_id}/summary", response_model=RunResponse)
def run_summary(project_id: UUID, run_id: UUID, x_user_id: str | None = Header(default=None)) -> RunResponse:
    user_id = get_current_user_id(x_user_id)
    projects = store.list_projects(owner_id=user_id)
    if not any(project.id == project_id for project in projects):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    run = store.get_run(project_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadi.")
    return run


@app.get("/api/projects/{project_id}/runs/{run_id}/hotspots")
def run_hotspots(project_id: UUID, run_id: UUID, x_user_id: str | None = Header(default=None)):
    user_id = get_current_user_id(x_user_id)
    projects = store.list_projects(owner_id=user_id)
    if not any(project.id == project_id for project in projects):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.build_hotspots(project_id, run_id)


@app.get("/api/projects/{project_id}/runs/{run_id}/dependency-graph")
def run_dependency_graph(project_id: UUID, run_id: UUID, x_user_id: str | None = Header(default=None)):
    user_id = get_current_user_id(x_user_id)
    projects = store.list_projects(owner_id=user_id)
    if not any(project.id == project_id for project in projects):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.build_graph(project_id, run_id)


@app.get("/api/projects/{project_id}/trends")
def project_trends(
    project_id: UUID,
    metric: Literal["mccabe_max", "mccabe_avg", "halstead_effort_total"] = Query(default="mccabe_avg"),
    x_user_id: str | None = Header(default=None),
):
    user_id = get_current_user_id(x_user_id)
    projects = store.list_projects(owner_id=user_id)
    if not any(project.id == project_id for project in projects):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.build_trend(project_id, metric=metric)
