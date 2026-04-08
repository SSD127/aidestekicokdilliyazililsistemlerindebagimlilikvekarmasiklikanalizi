from __future__ import annotations
import os
from dotenv import load_dotenv
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


# -------------------------------------------------
# Database setup
# -------------------------------------------------
load_dotenv(override=True)
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# -------------------------------------------------
# Enums
# -------------------------------------------------
class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class DependencyType(str, Enum):
    import_ = "import"
    call = "call"
    inheritance = "inheritance"
    composition = "composition"


# -------------------------------------------------
# SQLAlchemy models
# -------------------------------------------------
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    repo_url: Mapped[str] = mapped_column(Text, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(120), default="main", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list[AnalysisRun]] = relationship("AnalysisRun", back_populates="project", cascade="all, delete-orphan")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus), default=RunStatus.pending, nullable=False)
    commit_hash: Mapped[Optional[str]] = mapped_column(String(120))
    branch_name: Mapped[str] = mapped_column(String(120), default="main", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Project] = relationship("Project", back_populates="runs")
    files: Mapped[list[FileRecord]] = relationship("FileRecord", back_populates="run", cascade="all, delete-orphan")
    function_metrics: Mapped[list[FunctionMetric]] = relationship(
        "FunctionMetric", back_populates="run", cascade="all, delete-orphan"
    )
    dependencies: Mapped[list[Dependency]] = relationship(
        "Dependency", back_populates="run", cascade="all, delete-orphan"
    )
    hotspots: Mapped[list[Hotspot]] = relationship("Hotspot", back_populates="run", cascade="all, delete-orphan")
    metadata_row: Mapped[Optional[RunMetadata]] = relationship(
        "RunMetadata", back_populates="run", uselist=False, cascade="all, delete-orphan"
    )


class FileRecord(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("run_id", "path", name="uq_files_run_path"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    complexity_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    maintainability_index: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    dependency_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="files")
    metrics: Mapped[list[FunctionMetric]] = relationship(
        "FunctionMetric", back_populates="file", cascade="all, delete-orphan"
    )


class FunctionMetric(Base):
    __tablename__ = "function_metrics"
    __table_args__ = (
        UniqueConstraint("file_id", "function_name", "start_line", name="uq_function_per_file"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    function_name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_line: Mapped[Optional[int]] = mapped_column(Integer)
    end_line: Mapped[Optional[int]] = mapped_column(Integer)
    cyclomatic_complexity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    halstead_score: Mapped[Optional[float]] = mapped_column(Numeric(14, 4))
    loc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="function_metrics")
    file: Mapped[FileRecord] = relationship("FileRecord", back_populates="metrics")


class Dependency(Base):
    __tablename__ = "dependencies"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    source_file_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL"))
    target_file_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL"))
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    dependency_type: Mapped[DependencyType] = mapped_column(SAEnum(DependencyType), nullable=False)
    source_symbol: Mapped[Optional[str]] = mapped_column(String(255))
    target_symbol: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="dependencies")


class Hotspot(Base):
    __tablename__ = "hotspots"
    __table_args__ = (UniqueConstraint("run_id", "rank", name="uq_hotspot_rank_per_run"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    function_metric_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("function_metrics.id", ondelete="SET NULL")
    )
    function_name: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_score: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="hotspots")


class RunMetadata(Base):
    __tablename__ = "run_metadata"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    parser_version: Mapped[str] = mapped_column(String(120), nullable=False)
    grammar_version: Mapped[Optional[str]] = mapped_column(String(120))
    analyzer_version: Mapped[Optional[str]] = mapped_column(String(120))
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    commit_tag: Mapped[Optional[str]] = mapped_column(String(120))
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="metadata_row")


# -------------------------------------------------
# Pydantic schemas
# -------------------------------------------------
class ProjectCreate(BaseModel):
    owner_id: UUID
    name: str = Field(min_length=2, max_length=120)
    repo_url: str
    default_branch: str = "main"


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    repo_url: str
    default_branch: str
    created_at: datetime


class RunCreate(BaseModel):
    commit_hash: Optional[str] = None
    branch_name: str = "main"


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: RunStatus
    commit_hash: Optional[str]
    branch_name: str
    started_at: datetime
    finished_at: Optional[datetime]


class RunStatusUpdate(BaseModel):
    status: RunStatus
    error_message: Optional[str] = None


class FileIn(BaseModel):
    path: str
    language: str = "unknown"
    complexity_score: Optional[float] = None
    maintainability_index: Optional[float] = None
    dependency_count: int = 0
    loc: int = 0


class FunctionMetricIn(BaseModel):
    file_path: str
    function_name: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    cyclomatic_complexity: int = 0
    halstead_score: Optional[float] = None
    loc: int = 0
    risk_score: Optional[float] = None


class DependencyIn(BaseModel):
    source_path: str
    target_path: str
    dependency_type: DependencyType
    source_symbol: Optional[str] = None
    target_symbol: Optional[str] = None


class HotspotIn(BaseModel):
    file_path: str
    function_name: str
    risk_score: float
    reason: str
    rank: int = Field(ge=1, le=5)


class RunMetadataIn(BaseModel):
    parser_version: str
    grammar_version: Optional[str] = None
    analyzer_version: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    commit_tag: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class IngestPayload(BaseModel):
    files: list[FileIn] = Field(default_factory=list)
    function_metrics: list[FunctionMetricIn] = Field(default_factory=list)
    dependencies: list[DependencyIn] = Field(default_factory=list)
    hotspots: list[HotspotIn] = Field(default_factory=list)
    metadata: Optional[RunMetadataIn] = None


class SummaryOut(BaseModel):
    run_id: UUID
    project_id: UUID
    status: RunStatus
    file_count: int
    function_count: int
    dependency_count: int
    avg_cyclomatic_complexity: float
    max_cyclomatic_complexity: int
    total_halstead_score: float
    hotspot_count: int


class HotspotOut(BaseModel):
    function_name: str
    file_path: str
    risk_score: float
    reason: str
    rank: int


class DependencyGraphNode(BaseModel):
    id: str
    label: str


class DependencyGraphEdge(BaseModel):
    source: str
    target: str
    dependency_type: str


class DependencyGraphOut(BaseModel):
    nodes: list[DependencyGraphNode]
    edges: list[DependencyGraphEdge]


# -------------------------------------------------
# FastAPI setup
# -------------------------------------------------
app = FastAPI(title="Software Complexity Analysis API", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def get_project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_run_or_404(db: Session, project_id: UUID, run_id: UUID) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# -------------------------------------------------
# Project endpoints
# -------------------------------------------------
@app.post("/api/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


# -------------------------------------------------
# Run endpoints
# -------------------------------------------------
@app.post("/api/projects/{project_id}/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def create_run(project_id: UUID, payload: RunCreate, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    run = AnalysisRun(project_id=project_id, status=RunStatus.pending, **payload.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@app.get("/api/projects/{project_id}/runs", response_model=list[RunOut])
def list_runs(project_id: UUID, db: Session = Depends(get_db)):
    get_project_or_404(db, project_id)
    return (
        db.query(AnalysisRun)
        .filter(AnalysisRun.project_id == project_id)
        .order_by(AnalysisRun.started_at.desc())
        .all()
    )


@app.post("/api/internal/runs/{run_id}/status", response_model=RunOut)
def update_run_status(run_id: UUID, payload: RunStatusUpdate, db: Session = Depends(get_db)):
    run = db.get(AnalysisRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run.status = payload.status
    run.error_message = payload.error_message
    if payload.status in {RunStatus.completed, RunStatus.failed}:
        run.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


# -------------------------------------------------
# Ingest endpoint
# -------------------------------------------------
@app.post("/api/internal/runs/{run_id}/ingest")
def ingest_run_data(run_id: UUID, payload: IngestPayload, db: Session = Depends(get_db)):
    run = db.get(AnalysisRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Re-ingest protection
    if run.files or run.function_metrics or run.dependencies or run.hotspots:
        raise HTTPException(status_code=409, detail="This run already contains ingested data")

    path_to_file: dict[str, FileRecord] = {}

    for file_item in payload.files:
        record = FileRecord(run_id=run.id, **file_item.model_dump())
        db.add(record)
        db.flush()
        path_to_file[record.path] = record

    for metric in payload.function_metrics:
        file_record = path_to_file.get(metric.file_path)
        if not file_record:
            raise HTTPException(
                status_code=400,
                detail=f"Function metric references unknown file path: {metric.file_path}",
            )
        row = FunctionMetric(
            run_id=run.id,
            file_id=file_record.id,
            function_name=metric.function_name,
            start_line=metric.start_line,
            end_line=metric.end_line,
            cyclomatic_complexity=metric.cyclomatic_complexity,
            halstead_score=metric.halstead_score,
            loc=metric.loc,
            risk_score=metric.risk_score,
        )
        db.add(row)

    db.flush()

    metric_lookup: dict[tuple[str, str], FunctionMetric] = {}
    metrics = db.query(FunctionMetric).filter(FunctionMetric.run_id == run.id).all()
    for m in metrics:
        file_path = next((path for path, f in path_to_file.items() if f.id == m.file_id), None)
        if file_path:
            metric_lookup[(file_path, m.function_name)] = m

    for dep in payload.dependencies:
        source_file = path_to_file.get(dep.source_path)
        target_file = path_to_file.get(dep.target_path)
        db.add(
            Dependency(
                run_id=run.id,
                source_file_id=source_file.id if source_file else None,
                target_file_id=target_file.id if target_file else None,
                source_path=dep.source_path,
                target_path=dep.target_path,
                dependency_type=dep.dependency_type,
                source_symbol=dep.source_symbol,
                target_symbol=dep.target_symbol,
            )
        )

    for hot in payload.hotspots:
        file_record = path_to_file.get(hot.file_path)
        if not file_record:
            raise HTTPException(status_code=400, detail=f"Hotspot references unknown file path: {hot.file_path}")
        metric = metric_lookup.get((hot.file_path, hot.function_name))
        db.add(
            Hotspot(
                run_id=run.id,
                file_id=file_record.id,
                function_metric_id=metric.id if metric else None,
                function_name=hot.function_name,
                risk_score=hot.risk_score,
                reason=hot.reason,
                rank=hot.rank,
            )
        )

    if payload.metadata:
        db.add(
            RunMetadata(
                run_id=run.id,
                parser_version=payload.metadata.parser_version,
                grammar_version=payload.metadata.grammar_version,
                analyzer_version=payload.metadata.analyzer_version,
                analyzed_at=payload.metadata.analyzed_at or datetime.utcnow(),
                commit_tag=payload.metadata.commit_tag,
                extra=payload.metadata.extra,
            )
        )

    run.status = RunStatus.completed
    run.finished_at = datetime.utcnow()

    db.commit()
    return {
        "message": "Ingest completed successfully",
        "run_id": str(run.id),
        "files": len(payload.files),
        "function_metrics": len(payload.function_metrics),
        "dependencies": len(payload.dependencies),
        "hotspots": len(payload.hotspots),
    }


# -------------------------------------------------
# Read endpoints for frontend
# -------------------------------------------------
@app.get("/api/projects/{project_id}/runs/{run_id}/summary", response_model=SummaryOut)
def get_run_summary(project_id: UUID, run_id: UUID, db: Session = Depends(get_db)):
    run = get_run_or_404(db, project_id, run_id)

    file_count = db.query(FileRecord).filter(FileRecord.run_id == run.id).count()
    function_count = db.query(FunctionMetric).filter(FunctionMetric.run_id == run.id).count()
    dependency_count = db.query(Dependency).filter(Dependency.run_id == run.id).count()
    hotspot_count = db.query(Hotspot).filter(Hotspot.run_id == run.id).count()

    function_rows = db.query(FunctionMetric).filter(FunctionMetric.run_id == run.id).all()
    if function_rows:
        avg_cc = round(sum(r.cyclomatic_complexity for r in function_rows) / len(function_rows), 2)
        max_cc = max(r.cyclomatic_complexity for r in function_rows)
        total_halstead = round(sum(float(r.halstead_score or 0) for r in function_rows), 2)
    else:
        avg_cc = 0.0
        max_cc = 0
        total_halstead = 0.0

    return SummaryOut(
        run_id=run.id,
        project_id=run.project_id,
        status=run.status,
        file_count=file_count,
        function_count=function_count,
        dependency_count=dependency_count,
        avg_cyclomatic_complexity=avg_cc,
        max_cyclomatic_complexity=max_cc,
        total_halstead_score=total_halstead,
        hotspot_count=hotspot_count,
    )


@app.get("/api/projects/{project_id}/runs/{run_id}/hotspots", response_model=list[HotspotOut])
def get_run_hotspots(project_id: UUID, run_id: UUID, db: Session = Depends(get_db)):
    run = get_run_or_404(db, project_id, run_id)
    rows = (
        db.query(Hotspot, FileRecord.path)
        .join(FileRecord, Hotspot.file_id == FileRecord.id)
        .filter(Hotspot.run_id == run.id)
        .order_by(Hotspot.rank.asc())
        .all()
    )
    return [
        HotspotOut(
            function_name=hotspot.function_name,
            file_path=file_path,
            risk_score=float(hotspot.risk_score),
            reason=hotspot.reason,
            rank=hotspot.rank,
        )
        for hotspot, file_path in rows
    ]


@app.get("/api/projects/{project_id}/runs/{run_id}/dependency-graph", response_model=DependencyGraphOut)
def get_dependency_graph(project_id: UUID, run_id: UUID, db: Session = Depends(get_db)):
    run = get_run_or_404(db, project_id, run_id)
    files = db.query(FileRecord).filter(FileRecord.run_id == run.id).all()
    deps = db.query(Dependency).filter(Dependency.run_id == run.id).all()

    nodes = [DependencyGraphNode(id=f.path, label=f.path.split("/")[-1]) for f in files]
    edges = [
        DependencyGraphEdge(
            source=d.source_path,
            target=d.target_path,
            dependency_type=d.dependency_type.value,
        )
        for d in deps
    ]
    return DependencyGraphOut(nodes=nodes, edges=edges)


@app.get("/api/projects/{project_id}/trends")
def get_project_trends(
    project_id: UUID,
    metric: str = Query(pattern="^(mccabe_avg|mccabe_max|halstead_total|risk_total)$"),
    db: Session = Depends(get_db),
):
    get_project_or_404(db, project_id)
    runs = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.project_id == project_id)
        .order_by(AnalysisRun.started_at.asc())
        .all()
    )

    series = []
    for run in runs:
        metrics = db.query(FunctionMetric).filter(FunctionMetric.run_id == run.id).all()
        if not metrics:
            value = 0.0
        elif metric == "mccabe_avg":
            value = round(sum(m.cyclomatic_complexity for m in metrics) / len(metrics), 2)
        elif metric == "mccabe_max":
            value = max(m.cyclomatic_complexity for m in metrics)
        elif metric == "halstead_total":
            value = round(sum(float(m.halstead_score or 0) for m in metrics), 2)
        else:
            value = round(sum(float(m.risk_score or 0) for m in metrics), 2)

        series.append({
            "run_id": str(run.id),
            "started_at": run.started_at,
            "metric": metric,
            "value": value,
        })

    return {"project_id": str(project_id), "metric": metric, "series": series}


@app.get("/")
def healthcheck():
    return {"message": "Software Complexity Analysis API is running"}


# -------------------------------------------------
# Example ingest payload
# -------------------------------------------------
EXAMPLE_INGEST_PAYLOAD = {
    "files": [
        {
            "path": "src/analyzer.py",
            "language": "python",
            "complexity_score": 18.5,
            "maintainability_index": 72.4,
            "dependency_count": 3,
            "loc": 210,
        }
    ],
    "function_metrics": [
        {
            "file_path": "src/analyzer.py",
            "function_name": "analyze_project",
            "start_line": 12,
            "end_line": 89,
            "cyclomatic_complexity": 11,
            "halstead_score": 132.8,
            "loc": 77,
            "risk_score": 8.7,
        }
    ],
    "dependencies": [
        {
            "source_path": "src/analyzer.py",
            "target_path": "src/parser.py",
            "dependency_type": "import",
            "source_symbol": "analyze_project",
            "target_symbol": "parse_code",
        }
    ],
    "hotspots": [
        {
            "file_path": "src/analyzer.py",
            "function_name": "analyze_project",
            "risk_score": 8.7,
            "reason": "High cyclomatic complexity and long function body",
            "rank": 1,
        }
    ],
    "metadata": {
        "parser_version": "1.0.0",
        "grammar_version": "1.0.0",
        "analyzer_version": "1.0.0",
        "extra": {"language_count": 2},
    },
}

"""
Run locally:
    pip install fastapi uvicorn sqlalchemy pydantic
    uvicorn api_backend:app --reload

Suggested flow:
1) POST /api/projects
2) POST /api/projects/{project_id}/runs
3) POST /api/internal/runs/{run_id}/ingest
4) GET  /api/projects/{project_id}/runs/{run_id}/summary
5) GET  /api/projects/{project_id}/runs/{run_id}/hotspots
6) GET  /api/projects/{project_id}/runs/{run_id}/dependency-graph
"""

