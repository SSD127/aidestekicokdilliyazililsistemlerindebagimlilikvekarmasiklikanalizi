"""
Parser, metrik ve dependency modullerinden gelen ham veriyi
analysis_result.schema.json formatina donusturur.
"""
from datetime import datetime
from uuid import UUID

from app.core.risk import calculate_risk_level

RISK_SCORE_MAP = {"low": 1.0, "moderate": 5.0, "high": 10.0, "critical": 18.0}


def build_file_entry(
    path: str,
    language: str,
    loc: int,
    complexity_score: float,
    dependency_count: int,
    maintainability_index: float | None = None,
) -> dict:
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
    allowed = {"import", "call", "inheritance", "composition"}
    return {
        "source_path": source_path,
        "target_path": target_path,
        "dependency_type": dependency_type if dependency_type in allowed else "import",
        "source_symbol": source_symbol,
        "target_symbol": target_symbol,
    }


def build_hotspots(functions: list[dict], top_n: int = 5) -> list[dict]:
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
    Tum modul ciktilarini tek analysis_result payload'ina toplar.
    Bu yapi /api/internal/runs/{run_id}/ingest endpoint'ine gonderilir.
    """
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
