"""
payload_builder.py — Analiz Çıktısı Birleştirici

Bu dosya parser, metrik ve dependency modüllerinden gelen ham verileri
analysis_result.schema.json formatına dönüştüren yardımcı fonksiyonları içerir.

Sorumluluk:
  - Her modülün çıktısı için standart dict yapısı üretmek
  - Risk skorlarını hesaplayıp fonksiyon girişlerine eklemek
  - Hotspot listesini risk skoruna göre sıralayıp üretmek
  - Tüm modül çıktılarını tek bir ingest payload'ında birleştirmek

Bu dosya sayesinde modüller birbirinden bağımsız geliştirilip
aynı format üzerinden birleştirilebilir.
"""

from datetime import datetime
from uuid import UUID

from app.core.risk import calculate_risk_level

# Risk seviyesinden sayısal skora dönüşüm tablosu
RISK_SCORE_MAP = {"low": 1.0, "moderate": 5.0, "high": 10.0, "critical": 18.0}


def build_file_entry(
    path: str,
    language: str,
    loc: int,
    complexity_score: float,
    dependency_count: int,
    maintainability_index: float | None = None,
) -> dict:
    # Tek bir dosya için metrik kaydı oluşturur
    # schemas.py içindeki FileMetric modeli ile birebir uyumludur
    return {
        "path": path,
        "language": language,
        "loc": loc,
        "complexity_score": complexity_score,
        "dependency_count": dependency_count,
        "maintainability_index": maintainability_index,
    }


def build_function_entry(
    file_path: str,
    function_name: str,
    cyclomatic_complexity: int,
    halstead_score: float,
    loc: int,
    start_line: int = 1,
    end_line: int = 1,
) -> dict:
    # Tek bir fonksiyon için metrik kaydı oluşturur
    # Risk seviyesini otomatik hesaplayıp sayısal skora çevirir
    risk = calculate_risk_level(cyclomatic_complexity, halstead_score)
    return {
        "file_path": file_path,
        "function_name": function_name,
        "cyclomatic_complexity": cyclomatic_complexity,
        "halstead_score": halstead_score,
        "loc": loc,
        "start_line": start_line,
        "end_line": end_line,
        "risk_score": RISK_SCORE_MAP[risk],
    }


def build_dependency_entry(
    source_path: str,
    target_path: str,
    dependency_type: str = "import",
    source_symbol: str | None = None,
    target_symbol: str | None = None,
) -> dict:
    # İki dosya arasındaki bağımlılık kenarı kaydı oluşturur
    # dependency_type sadece izin verilen değerlerden biri olabilir; bilinmeyenler "import" olur
    allowed = {"import", "call", "inheritance", "composition"}
    return {
        "source_path": source_path,
        "target_path": target_path,
        "dependency_type": dependency_type if dependency_type in allowed else "import",
        "source_symbol": source_symbol,
        "target_symbol": target_symbol,
    }


def build_hotspots(functions: list[dict], top_n: int = 5) -> list[dict]:
    # Fonksiyon listesini risk skoruna göre sıralayıp en riskli top_n tanesini döndürür
    # Hotspot listesi frontend'de "En Riskli 5 Fonksiyon" tablosunda gösterilir
    sorted_fns = sorted(functions, key=lambda f: f.get("risk_score", 0), reverse=True)
    hotspots = []
    for rank, fn in enumerate(sorted_fns[:top_n], start=1):
        cc = fn.get("cyclomatic_complexity", 0)
        hotspots.append({
            "file_path": fn["file_path"],
            "function_name": fn["function_name"],
            "risk_score": fn.get("risk_score", 0),
            "reason": f"Cyclomatic complexity: {cc}",
            "rank": rank,
        })
    return hotspots


def build_analysis_payload(
    run_id: UUID,
    project_id: UUID,
    branch_name: str,
    commit_hash: str,
    parser_version: str,
    files: list[dict],
    functions: list[dict],
    dependencies: list[dict],
    grammar_version: str | None = None,
) -> dict:
    """
    Tüm modül çıktılarını tek bir analysis_result payload'ında birleştirir.

    Bu payload /api/internal/runs/{run_id}/ingest endpoint'ine gönderilir
    ve AnalysisResult Pydantic modeli ile doğrulanır.
    Referans format: backend/contracts/examples/golden_analysis_result.json
    """
    # Fonksiyon listesinden otomatik hotspot üret
    hotspots = build_hotspots(functions)
    return {
        "run_id": str(run_id),
        "project_id": str(project_id),
        "branch_name": branch_name,
        "commit_hash": commit_hash,
        "analyzed_at": datetime.utcnow().isoformat() + "Z",
        "parser_version": parser_version,
        "grammar_version": grammar_version,
        "files": files,
        "functions": functions,
        "dependencies": dependencies,
        "hotspots": hotspots,
    }
