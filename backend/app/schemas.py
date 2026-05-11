"""
schemas.py — Veri Sözleşmeleri (Request / Response Modelleri)

Bu dosya PolyMetric API'sinin tüm giriş ve çıkış veri yapılarını tanımlar.
Frontend'in ne göndereceğini, backend'in ne döndüreceğini ve analiz motorunun
hangi formatta veri yazacağını belirleyen tek referans noktasıdır.
Pydantic modelleri sayesinde tip hatası ve eksik alan varsa otomatik 422 döner.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl

# Run'ın alabileceği durumlar — geçişler storage.py içinde zorlanır
RunStatus = Literal["pending", "running", "completed", "failed"]


# ---------------------------------------------------------------------------
# Proje modelleri
# ---------------------------------------------------------------------------

class ProjectCreateRequest(BaseModel):
    # Kullanıcının yeni proje oluştururken gönderdiği veri
    name: str = Field(min_length=2, max_length=120)
    github_repo_url: HttpUrl
    default_branch: str = "main"


class ProjectResponse(BaseModel):
    # API'nin projeyi döndürürken kullandığı format
    id: UUID
    owner_id: str
    name: str
    github_repo_url: str
    default_branch: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Analiz run modelleri
# ---------------------------------------------------------------------------

class RunCreateRequest(BaseModel):
    # Kullanıcının analiz başlatırken belirtebileceği branch/tag/commit
    github_ref: str | None = None


class AnalyzeRequest(BaseModel):
    """
    POST /api/analyze sarmalayıcı endpoint'inin request gövdesi.
    Frontend tek seferde GitHub URL gönderir, backend senkron analiz yapıp
    AnalysisResult döndürür.
    """
    github_url: HttpUrl
    branch: str = "main"
    # include_tests şimdilik kabul edilir ama yok sayılır; gelecekte test dosyalarını
    # filtrelemek için kullanılacak
    include_tests: bool = True


class RunResponse(BaseModel):
    # Analiz run'ının mevcut durumunu ve meta bilgilerini döndürür
    id: UUID
    project_id: UUID
    status: RunStatus
    github_ref: str
    parser_version: str
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Analiz çıktı modelleri — frontend görselleştirme için
# ---------------------------------------------------------------------------

class HotspotItem(BaseModel):
    # En riskli fonksiyonları listeleyen yapı; frontend tabloda gösterir
    function_name: str
    score: float
    label: str = "kritik uyari"
    rank: int


class DependencyNode(BaseModel):
    # Bağımlılık grafiğindeki bir düğüm (dosya veya modül)
    id: str
    label: str


class DependencyEdge(BaseModel):
    # İki düğüm arasındaki yönlü bağımlılık kenarı
    source: str
    target: str
    relation_type: str


class DependencyGraphResponse(BaseModel):
    # Tüm bağımlılık grafiğini düğüm ve kenar listeleriyle döndürür
    nodes: list[DependencyNode]
    edges: list[DependencyEdge]


class TrendPoint(BaseModel):
    # Tek bir run'a ait trend noktası; zaman içi değişimi göstermek için kullanılır
    run_id: UUID
    created_at: datetime
    value: float


class TrendResponse(BaseModel):
    # Seçilen metrik için tüm run'ların trend noktalarını döndürür
    metric: str
    points: list[TrendPoint]


# ---------------------------------------------------------------------------
# Analiz motoru ingest payload modelleri
# ---------------------------------------------------------------------------

class FileMetric(BaseModel):
    # Analiz edilen tek bir dosyanın metrikleri
    path: str = Field(min_length=1)
    language: str = Field(min_length=1)
    loc: int = Field(ge=0, default=0)
    complexity_score: float = Field(ge=0.0, default=0.0)
    dependency_count: int = Field(ge=0, default=0)
    maintainability_index: float | None = None


class FunctionMetric(BaseModel):
    # Dosya içindeki tek bir fonksiyonun metrikleri
    file_path: str
    function_name: str = Field(min_length=1)
    cyclomatic_complexity: int = Field(ge=0)
    halstead_score: float = Field(ge=0.0, default=0.0)
    loc: int = Field(ge=0, default=0)
    start_line: int = Field(ge=1, default=1)
    end_line: int = Field(ge=1, default=1)
    risk_score: float = Field(ge=0.0, default=0.0)
    icc_density: float | None = None


class DependencyEntry(BaseModel):
    # İki dosya arasındaki bağımlılık ilişkisi
    source_path: str
    target_path: str
    dependency_type: Literal["import", "call", "inheritance", "composition"] = "import"
    source_symbol: str | None = None
    target_symbol: str | None = None


class HotspotEntry(BaseModel):
    # Analiz motorunun belirlediği riskli fonksiyon kaydı
    file_path: str
    function_name: str
    risk_score: float = Field(ge=0.0)
    reason: str
    rank: int = Field(ge=1, le=5)


class CycleEntry(BaseModel):
    nodes: list[str]
    length: int
    chain: str


class GraphMetricEntry(BaseModel):
    total_nodes: int
    total_edges: int
    total_cycles: int
    density: float
    avg_in_degree: float
    avg_out_degree: float
    max_in_degree: dict
    max_out_degree: dict
    strongly_connected_components: int
    instability_scores: dict[str, float]


class AnalysisResult(BaseModel):
    """
    Analiz motorunun /api/internal/runs/{run_id}/ingest endpoint'ine
    göndereceği tam payload yapısı.
    analysis_result.schema.json ile birebir uyumludur.
    Tip uyuşmazlığı veya eksik alan varsa otomatik 422 döner.
    """
    run_id: UUID
    project_id: UUID
    commit_hash: str = Field(min_length=7)
    branch_name: str = Field(min_length=1)
    analyzed_at: datetime
    parser_version: str
    grammar_version: str | None = None
    commit_tag: str | None = None
    files: list[FileMetric]
    functions: list[FunctionMetric]
    nodes: list[dict] = []
    dependencies: list[DependencyEntry]
    cycles: list[CycleEntry] = []
    graph_metrics: GraphMetricEntry | None = None
    hotspots: list[HotspotEntry] = Field(max_length=5)


# ---------------------------------------------------------------------------
# Yardımcı fonksiyon
# ---------------------------------------------------------------------------

def make_project_response(owner_id: str, payload: ProjectCreateRequest) -> ProjectResponse:
    # Yeni proje için benzersiz ID ve oluşturma zamanı atayarak ProjectResponse döndürür
    return ProjectResponse(
        id=uuid4(),
        owner_id=owner_id,
        name=payload.name,
        github_repo_url=str(payload.github_repo_url),
        default_branch=payload.default_branch,
        created_at=datetime.utcnow(),
    )
