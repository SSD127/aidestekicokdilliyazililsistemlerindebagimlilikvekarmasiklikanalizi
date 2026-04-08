"""
storage.py — Geçici Bellek İçi Veri Deposu (In-Memory Store)

Bu dosya proje ve analiz run verilerini RAM'de tutar.
Supabase/PostgreSQL entegrasyonu tamamlanana kadar geçici veri katmanı olarak kullanılır.
Uygulama yeniden başlatıldığında tüm veriler sıfırlanır.

NOT: Supabase repository katmanı hazır olduğunda bu dosya tamamen kaldırılacaktır.
"""

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
    # Projeleri id → ProjectResponse eşlemesiyle saklar
    projects: dict[UUID, ProjectResponse] = field(default_factory=dict)

    # Her projeye ait run listesini saklar
    runs_by_project: dict[UUID, list[RunResponse]] = field(
        default_factory=lambda: defaultdict(list)
    )

    # İngest edilen analiz payload'larını run_id → dict olarak saklar
    analysis_data: dict[UUID, dict] = field(default_factory=dict)

    # Geçerli run durum geçişlerini tanımlar; kuraldışı geçişleri engeller
    # Örnek: completed → running geçişi yasaktır
    allowed_run_transitions: dict[str, set[str]] = field(
        default_factory=lambda: {
            "pending": {"running", "failed"},
            "running": {"completed", "failed"},
            "completed": set(),
            "failed": set(),
        }
    )

    def create_project(self, owner_id: str, payload: ProjectCreateRequest) -> ProjectResponse:
        # Yeni proje oluşturur ve belleğe kaydeder
        project = make_project_response(owner_id, payload)
        self.projects[project.id] = project
        return project

    def list_projects(self, owner_id: str) -> list[ProjectResponse]:
        # Sadece ilgili kullanıcıya ait projeleri döndürür
        return [p for p in self.projects.values() if p.owner_id == owner_id]

    def create_run(self, project_id: UUID, payload: RunCreateRequest) -> RunResponse:
        # Yeni analiz run'ı oluşturur; başlangıç durumu her zaman 'pending'dir
        run = RunResponse(
            id=uuid4(),
            project_id=project_id,
            status="pending",
            github_ref=payload.github_ref or "main",
            parser_version="tree-sitter:v0.25",
            started_at=datetime.utcnow(),
        )
        self.runs_by_project[project_id].append(run)
        return run

    def list_runs(self, project_id: UUID) -> list[RunResponse]:
        # Bir projeye ait tüm run'ları döndürür
        return self.runs_by_project[project_id]

    def get_run(self, project_id: UUID, run_id: UUID) -> RunResponse | None:
        # Proje ve run id'sine göre tek bir run döndürür; bulunamazsa None
        for run in self.runs_by_project.get(project_id, []):
            if run.id == run_id:
                return run
        return None

    def get_run_by_id(self, run_id: UUID) -> RunResponse | None:
        # Sadece run id'si bilindiğinde tüm projeler içinde arama yapar
        for runs in self.runs_by_project.values():
            for run in runs:
                if run.id == run_id:
                    return run
        return None

    def update_run_status(self, run_id: UUID, status: str, error_message: str | None = None) -> bool:
        # Run durumunu günceller; izin verilmeyen geçişlerde ValueError fırlatır
        for runs in self.runs_by_project.values():
            for i, run in enumerate(runs):
                if run.id == run_id:
                    # Geçersiz durum geçişini engelle
                    if run.status != status and status not in self.allowed_run_transitions.get(run.status, set()):
                        raise ValueError(f"Gecersiz state gecisi: {run.status} -> {status}")

                    # completed veya failed durumuna geçince bitiş zamanını kaydet
                    finished = datetime.utcnow() if status in {"completed", "failed"} else None
                    runs[i] = RunResponse(
                        id=run.id,
                        project_id=run.project_id,
                        status=status,  # type: ignore[arg-type]
                        github_ref=run.github_ref,
                        parser_version=run.parser_version,
                        started_at=run.started_at,
                        finished_at=finished,
                        error_message=error_message,
                    )
                    return True
        return False

    def ingest_analysis(self, run_id: UUID, payload: dict) -> None:
        # Analiz motorunun gönderdiği payload'ı run_id ile ilişkilendirerek saklar
        self.analysis_data[run_id] = payload

    def build_hotspots(self, project_id: UUID, run_id: UUID) -> list[HotspotItem]:
        # İngest edilen payload'dan en riskli 5 fonksiyonu çıkarır
        run = self.get_run(project_id, run_id)
        if not run:
            return []
        data = self.analysis_data.get(run_id)
        if not data:
            return []
        return [
            HotspotItem(
                function_name=h["function_name"],
                score=h["risk_score"],
                label=h["reason"],
                rank=h["rank"],
            )
            for h in data.get("hotspots", [])
        ]

    def build_graph(self, project_id: UUID, run_id: UUID) -> DependencyGraphResponse:
        # İngest edilen bağımlılık listesinden düğüm ve kenar yapısı üretir
        run = self.get_run(project_id, run_id)
        if not run:
            return DependencyGraphResponse(nodes=[], edges=[])
        data = self.analysis_data.get(run_id)
        if not data:
            return DependencyGraphResponse(nodes=[], edges=[])

        # Kaynak ve hedef dosya yollarından benzersiz düğüm listesi oluştur
        node_ids: set[str] = set()
        for dep in data.get("dependencies", []):
            node_ids.add(dep["source_path"])
            node_ids.add(dep["target_path"])

        nodes = [DependencyNode(id=n, label=n) for n in sorted(node_ids)]
        edges = [
            DependencyEdge(
                source=dep["source_path"],
                target=dep["target_path"],
                relation_type=dep["dependency_type"],
            )
            for dep in data.get("dependencies", [])
        ]
        return DependencyGraphResponse(nodes=nodes, edges=edges)

    def build_trend(self, project_id: UUID, metric: str) -> TrendResponse:
        # Seçilen metrik için sadece tamamlanmış run'lardan trend noktaları üretir
        metric_map = {
            "mccabe_avg": lambda d: (
                sum(f["complexity_score"] for f in d.get("files", []))
                / max(len(d.get("files", [])), 1)
            ),
            "mccabe_max": lambda d: max(
                (f["complexity_score"] for f in d.get("files", [])), default=0.0
            ),
            "halstead_effort_total": lambda d: sum(
                fn.get("halstead_score", 0) for fn in d.get("functions", [])
            ),
        }
        extractor = metric_map.get(metric, lambda d: 0.0)
        points: list[TrendPoint] = []
        for run in self.runs_by_project.get(project_id, []):
            # Sadece tamamlanmış run'lar trend hesabına dahil edilir
            if run.status != "completed":
                continue
            data = self.analysis_data.get(run.id, {})
            points.append(TrendPoint(
                run_id=run.id,
                created_at=run.started_at,
                value=extractor(data),
            ))
        return TrendResponse(metric=metric, points=points)


# Uygulama genelinde tek bir store örneği kullanılır
store = InMemoryStore()
