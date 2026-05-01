"""
PolyMetric'in uçtan uca analiz akışını yöneten modül.
GitHub'dan repo indirir, Tree-sitter parser'ını çalıştırır, McCabe, Halstead
ve ICC metriklerini hesaplar, dosyalar arası bağımlılıkları çıkarır ve tüm sonuçları
analysis_result.schema.json formatında tek payload olarak birleştirir.
"""
from __future__ import annotations
import hashlib
import logging
import time
from uuid import UUID

from app.core.parser import (
    GRAMMAR_VERSION_PYTHON,
    PARSER_VERSION as PARSER_LIB_VERSION,
    parse_file,
)
from app.core.payload_builder import (
    build_analysis_payload,
    build_dependency_entry,
    build_file_entry,
    build_function_entry,
)

# HALİL'İN  OLAN METRİK MOTORU BURAYA EKLENDİ
# metric_engine.py dosyasının app/core/ klasöründe olduğunu varsayıyoruz
from app.core.metric_engine import ComplexityAnalyzer

logger = logging.getLogger(__name__)

# Run metadata'sına yazılacak parser sürümü
PARSER_VERSION = PARSER_LIB_VERSION

def run_parser(files: list[dict]) -> tuple[list[dict], list[dict]]:
    parsed: list[dict] = []
    skipped: list[dict] = []
    for f in files:
        try:
            parsed.append(parse_file(f["path"], f["content"], f["language"]))
        except NotImplementedError:
            skipped.append({"path": f["path"], "error": f"language not supported: {f['language']}"})
        except Exception as exc:
            logger.warning("Parse hatasi atlandi: %s — %s", f["path"], exc)
            skipped.append({"path": f["path"], "error": str(exc)})
    return parsed, skipped


def run_metrics(parsed_files: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Parser çıktısını HALİL'İN METRİK MOTORU'na gönderir ve
    dosya ile fonksiyon düzeyinde profesyonel metrik listeleri üretir.
    """
    file_metrics: list[dict] = []
    function_metrics: list[dict] = []

    for pf in parsed_files:
        path = pf["file_path"]
        language = pf.get("language", "python")
        summary = pf.get("summary", {})
        dosya_loc = summary.get("loc_code", 0)

        dosya_toplam_karmasiklik = 0

        # Parser'dan gelen fonksiyon listesini alıyoruz
        fonksiyonlar = pf.get("functions", [])

        # Her bir fonksiyon için senin V8 motorunu çalıştırıyoruz
        for func_data in fonksiyonlar:
            # 1. Kontağı çevir: Sadece bu fonksiyona özel motoru yarat
            motor = ComplexityAnalyzer(func_data)
            
            # 2. Gaza bas: Raporu üret
            fonk_rapor = motor.analiz_raporu_uret(dosya_loc_degeri=dosya_loc)
            
            # Dosyanın toplam karmaşıklığına (WMC) bu fonksiyonun skorunu ekle
            dosya_toplam_karmasiklik += fonk_rapor["cyclomatic_complexity"]

            # Fonksiyon karnesini listeye ekle
            function_metrics.append(build_function_entry(
                file_path=path,
                function_name=fonk_rapor["function_name"],
                cyclomatic_complexity=fonk_rapor["cyclomatic_complexity"],
                halstead_score=fonk_rapor["halstead_score"],
                loc=dosya_loc,
            ))

        # Dosya düzeyindeki karneleri listeye ekle
        file_metrics.append(build_file_entry(
            path=path,
            language=language,
            loc=dosya_loc,
            complexity_score=float(dosya_toplam_karmasiklik),
            dependency_count=summary.get("import_count", 0),
        ))

    return file_metrics, function_metrics


def run_dependency_scan(parsed_files: list[dict]) -> list[dict]:
    path_index = {pf["file_path"] for pf in parsed_files}
    deps: list[dict] = []
    for pf in parsed_files:
        source_path = pf["file_path"]
        for imp in pf.get("imports", []):
            module = imp.get("module") if isinstance(imp, dict) else None
            if not module or module == "?":
                continue
            candidate = module.replace(".", "/") + ".py"
            if candidate in path_index:
                deps.append(build_dependency_entry(
                    source_path=source_path,
                    target_path=candidate,
                    dependency_type="import",
                ))
    return deps


def analyze_repo(
    run_id: UUID,
    project_id: UUID,
    repo_url: str,
    ref: str = "main",
) -> dict:
    logger.info("Analiz basliyor: run_id=%s repo=%s ref=%s", run_id, repo_url, ref)
    timing: dict[str, float] = {}

    # (Buradaki download_repo importu muhtemelen yukarıda başka bir modülden geliyor, 
    # senkronizasyon için bırakıyorum, eğer yoksa app.services.github_pipeline'dan eklenmeli)
    from app.services.github_pipeline import download_repo 

    t0 = time.perf_counter()
    files = download_repo(repo_url, ref=ref)
    timing["download_sec"] = round(time.perf_counter() - t0, 3)
    logger.info("%d kaynak dosya indirildi (%.2fs)", len(files), timing["download_sec"])

    t0 = time.perf_counter()
    parsed, skipped = run_parser(files)
    timing["parsing_sec"] = round(time.perf_counter() - t0, 3)
    if skipped:
        logger.warning("%d dosya atlandi", len(skipped))

    t0 = time.perf_counter()
    file_metrics, function_metrics = run_metrics(parsed)
    dependencies = run_dependency_scan(parsed)
    timing["metrics_sec"] = round(time.perf_counter() - t0, 3)

    timing["total_sec"] = round(sum(timing.values()), 3)

    content_blob = "".join(f["content"] for f in files)
    commit_hash = hashlib.sha1(content_blob.encode()).hexdigest()[:12]

    payload = build_analysis_payload(
        run_id=run_id,
        project_id=project_id,
        branch_name=ref,
        commit_hash=commit_hash,
        parser_version=PARSER_VERSION,
        grammar_version=GRAMMAR_VERSION_PYTHON,
        files=file_metrics,
        functions=function_metrics,
        dependencies=dependencies,
    )
    payload["timing"] = timing
    payload["skipped_files"] = skipped
    payload["partial"] = len(skipped) > 0
    return payload