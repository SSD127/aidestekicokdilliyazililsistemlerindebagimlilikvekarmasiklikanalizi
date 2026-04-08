"""
main.py — FastAPI Uygulama Giriş Noktası ve HTTP Endpoint'leri

Bu dosya PolyMetric backend'inin ana API katmanıdır.
Kullanıcıdan gelen HTTP isteklerini alır, kimlik doğrulama yapar,
iş mantığını storage ve core modüllerine delege eder ve sonucu döndürür.

Endpoint grupları:
  - /api/projects       → Proje yönetimi (oluştur, listele)
  - /api/projects/.../runs → Analiz run yönetimi (başlat, listele, detay)
  - /api/projects/.../runs/.../... → Analiz çıktıları (hotspot, graph, trend, ai-insight)
  - /api/internal/runs/... → Analiz motoru için dahili yazma uçları (ingest, status)
"""

import asyncio
import logging
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Query, status
from pydantic import ValidationError
from requests import RequestException

from app.config import get_settings
from app.schemas import AnalysisResult, ProjectCreateRequest, ProjectResponse, RunCreateRequest, RunResponse
from app.services.ai_insight import generate_ai_insight
from app.services.github_pipeline import RepoTooLargeError, validate_github_repo_url
from app.storage import store

logger = logging.getLogger(__name__)
settings = get_settings()

# FastAPI uygulaması — uygulama adı ve debug modu config'den okunur
app = FastAPI(title=settings.app_name, debug=settings.app_debug)


# ---------------------------------------------------------------------------
# Kimlik doğrulama yardımcıları
# ---------------------------------------------------------------------------

def get_current_user_id(x_user_id: str | None) -> str:
    # Supabase JWT aktif olana kadar X-User-Id header'ından kullanıcı kimliği alınır
    # Header gönderilmezse geliştirme ortamı için varsayılan kullanıcı döner
    # TODO: Supabase JWT dogrulamasi ile degistir.
    return x_user_id or "local-dev-user"


def ensure_internal_access(x_internal_api_key: str | None) -> None:
    # Internal endpoint'lere erişimi INTERNAL_API_KEY ile kısıtlar
    # Anahtar .env'de tanımlı değilse endpoint tamamen kapalıdır
    if not settings.internal_api_key:
        raise HTTPException(
            status_code=503,
            detail="INTERNAL_API_KEY ayarlanmamis. Internal endpointler kapali.",
        )
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Gecersiz internal API key.")


# ---------------------------------------------------------------------------
# Sağlık kontrolü
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    # Uygulamanın ayakta olduğunu ve hangi ortamda çalıştığını döndürür
    return {"status": "ok", "env": settings.app_env}


# ---------------------------------------------------------------------------
# Proje endpoint'leri
# ---------------------------------------------------------------------------

@app.post("/api/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreateRequest, x_user_id: str | None = Header(default=None)) -> ProjectResponse:
    # Yeni proje oluşturur; GitHub URL geçerliliğini kontrol eder
    user_id = get_current_user_id(x_user_id)
    if not validate_github_repo_url(str(payload.github_repo_url)):
        raise HTTPException(status_code=400, detail="Gecerli bir GitHub repo URL giriniz.")
    return store.create_project(owner_id=user_id, payload=payload)


@app.get("/api/projects", response_model=list[ProjectResponse])
def list_projects(x_user_id: str | None = Header(default=None)) -> list[ProjectResponse]:
    # Sadece kimliği doğrulanmış kullanıcının projelerini döndürür
    return store.list_projects(owner_id=get_current_user_id(x_user_id))


# ---------------------------------------------------------------------------
# Run endpoint'leri
# ---------------------------------------------------------------------------

@app.post("/api/projects/{project_id}/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    project_id: UUID,
    payload: RunCreateRequest,
    x_user_id: str | None = Header(default=None),
) -> RunResponse:
    # Yeni analiz run'ı oluşturur ve analizi arka planda başlatır
    user_id = get_current_user_id(x_user_id)
    projects = store.list_projects(owner_id=user_id)
    project = next((p for p in projects if p.id == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    run = store.create_run(project_id=project_id, payload=payload)

    # Analizi thread pool'da arka planda çalıştır; kullanıcı hemen pending run alır
    ref = payload.github_ref or project.default_branch
    asyncio.get_event_loop().run_in_executor(
        None, _run_analysis_background, run.id, project_id, project.github_repo_url, ref
    )
    return run


def _run_analysis_background(run_id: UUID, project_id: UUID, repo_url: str, ref: str) -> None:
    # Arka planda çalışan analiz fonksiyonu
    # Orchestrator'ı çağırır; hata durumunda run'ı failed olarak işaretler
    from app.core.orchestrator import analyze_repo
    store.update_run_status(run_id, "running")
    try:
        payload = analyze_repo(run_id=run_id, project_id=project_id, repo_url=repo_url, ref=ref)
        store.ingest_analysis(run_id, payload)
        store.update_run_status(run_id, "completed")
    except RepoTooLargeError as exc:
        logger.warning("Repo cok buyuk run_id=%s: %s", run_id, exc)
        store.update_run_status(run_id, "failed", error_message=str(exc))
    except Exception as exc:
        logger.exception("Analiz hatasi run_id=%s", run_id)
        store.update_run_status(run_id, "failed", error_message=str(exc))


@app.get("/api/projects/{project_id}/runs", response_model=list[RunResponse])
def list_runs(project_id: UUID, x_user_id: str | None = Header(default=None)) -> list[RunResponse]:
    # Bir projeye ait tüm run'ları listeler; proje sahipliği kontrol edilir
    user_id = get_current_user_id(x_user_id)
    if not any(p.id == project_id for p in store.list_projects(owner_id=user_id)):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.list_runs(project_id)


@app.get("/api/projects/{project_id}/runs/{run_id}/summary", response_model=RunResponse)
def run_summary(project_id: UUID, run_id: UUID, x_user_id: str | None = Header(default=None)) -> RunResponse:
    # Tek bir run'ın durum ve meta bilgilerini döndürür
    user_id = get_current_user_id(x_user_id)
    if not any(p.id == project_id for p in store.list_projects(owner_id=user_id)):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    run = store.get_run(project_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadi.")
    return run


# ---------------------------------------------------------------------------
# Analiz çıktı endpoint'leri
# ---------------------------------------------------------------------------

@app.get("/api/projects/{project_id}/runs/{run_id}/hotspots")
def run_hotspots(project_id: UUID, run_id: UUID, x_user_id: str | None = Header(default=None)):
    # En yüksek risk skoruna sahip 5 fonksiyonu döndürür; frontend tablo/ısı haritası için kullanır
    user_id = get_current_user_id(x_user_id)
    if not any(p.id == project_id for p in store.list_projects(owner_id=user_id)):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.build_hotspots(project_id, run_id)


@app.get("/api/projects/{project_id}/runs/{run_id}/dependency-graph")
def run_dependency_graph(project_id: UUID, run_id: UUID, x_user_id: str | None = Header(default=None)):
    # Dosyalar arası bağımlılık grafiğini düğüm ve kenar listesi olarak döndürür
    user_id = get_current_user_id(x_user_id)
    if not any(p.id == project_id for p in store.list_projects(owner_id=user_id)):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.build_graph(project_id, run_id)


@app.get("/api/projects/{project_id}/trends")
def project_trends(
    project_id: UUID,
    metric: Literal["mccabe_max", "mccabe_avg", "halstead_effort_total"] = Query(default="mccabe_avg"),
    x_user_id: str | None = Header(default=None),
):
    # Seçilen metrik için run bazlı trend noktalarını döndürür; frontend çizgi grafiği için kullanır
    user_id = get_current_user_id(x_user_id)
    if not any(p.id == project_id for p in store.list_projects(owner_id=user_id)):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    return store.build_trend(project_id, metric=metric)


@app.get("/api/projects/{project_id}/runs/{run_id}/ai-insight")
def run_ai_insight(project_id: UUID, run_id: UUID, x_user_id: str | None = Header(default=None)):
    # Tamamlanmış bir run'ın metriklerini AI'a göndererek kısa Türkçe yorum üretir
    # OpenAI/Gemini API anahtarı yoksa kural tabanlı fallback devreye girer
    user_id = get_current_user_id(x_user_id)
    if not any(p.id == project_id for p in store.list_projects(owner_id=user_id)):
        raise HTTPException(status_code=404, detail="Proje bulunamadi.")
    run = store.get_run(project_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadi.")
    if run.status != "completed":
        raise HTTPException(status_code=409, detail="AI yorum icin run status 'completed' olmali.")

    # AI'ya gönderilecek özet veriyi hazırla
    run_summary_data = {
        "run": run.model_dump(mode="json"),
        "hotspots": [h.model_dump(mode="json") for h in store.build_hotspots(project_id, run_id)],
        "trend_snapshot": store.build_trend(project_id, metric="mccabe_avg").model_dump(mode="json"),
        "dependency_graph_size": {
            "node_count": len(store.build_graph(project_id, run_id).nodes),
            "edge_count": len(store.build_graph(project_id, run_id).edges),
        },
    }
    try:
        return generate_ai_insight(
            run_summary_data,
            settings.openai_api_key,
            settings.gemini_api_key,
        )
    except RequestException as exc:
        raise HTTPException(status_code=502, detail=f"AI servis hatasi: {exc}")


# ---------------------------------------------------------------------------
# Internal endpoint'ler — sadece analiz motoru tarafından kullanılır
# ---------------------------------------------------------------------------

@app.post("/api/internal/runs/{run_id}/status", status_code=status.HTTP_200_OK)
def update_run_status(
    run_id: UUID,
    body: dict,
    x_internal_api_key: str | None = Header(default=None),
):
    # Analiz motorunun run durumunu güncellemesi için kullanılır
    # Geçersiz durum geçişlerinde 409, bulunamazsa 404 döner
    ensure_internal_access(x_internal_api_key)
    new_status = body.get("status")
    if new_status not in {"pending", "running", "completed", "failed"}:
        raise HTTPException(status_code=400, detail="Gecersiz status degeri.")
    try:
        updated = store.update_run_status(run_id, new_status, body.get("error_message"))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail="Run bulunamadi.")
    return {"run_id": str(run_id), "status": new_status}


@app.post("/api/internal/runs/{run_id}/ingest", status_code=status.HTTP_201_CREATED)
def ingest_analysis(
    run_id: UUID,
    payload: dict,
    x_internal_api_key: str | None = Header(default=None),
):
    # Analiz motorunun tüm analiz çıktısını tek seferde yazdığı endpoint
    # Payload AnalysisResult Pydantic modeli ile doğrulanır; hata varsa 422 döner
    ensure_internal_access(x_internal_api_key)

    # Run'ın var olduğunu doğrula
    run = None
    for runs in store.runs_by_project.values():
        for r in runs:
            if r.id == run_id:
                run = r
                break
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadi.")

    # Payload şema kontrolü — analysis_result.schema.json ile uyumlu olmalı
    try:
        AnalysisResult(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())

    store.ingest_analysis(run_id, payload)

    # Veri yazıldıktan sonra run'ı completed olarak işaretle
    try:
        store.update_run_status(run_id, "completed")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"run_id": str(run_id), "ingested": True}
