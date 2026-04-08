"""
Analiz orkestratoru.
Parser, metrik ve dependency modullerini sirayla cagirır,
sonuclari payload_builder ile birlestirip storage'a yazar.
"""
import hashlib
import logging
import re
import time
from uuid import UUID

from app.core.payload_builder import (
    build_analysis_payload,
    build_dependency_entry,
    build_file_entry,
    build_function_entry,
)
from app.services.github_pipeline import download_repo

logger = logging.getLogger(__name__)

PARSER_VERSION = "stub:v0.1"


# ---------------------------------------------------------------------------
# Stub parser — tree-sitter entegre edilene kadar regex tabanli analiz
# ---------------------------------------------------------------------------

def _stub_parse_python(path: str, content: str) -> dict:
    lines = content.splitlines()
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
    functions = re.findall(r"^\s*(?:async\s+)?def\s+(\w+)", content, re.MULTILINE)
    imports = re.findall(r"^\s*(?:import|from)\s+([\w.]+)", content, re.MULTILINE)
    branches = len(re.findall(r"\b(?:if|elif|else|except|case)\b", content))
    loops = len(re.findall(r"\b(?:for|while)\b", content))
    return {
        "path": path, "language": "python", "loc": loc,
        "functions": functions, "branches": branches,
        "loops": loops, "imports": imports,
    }


def _stub_parse_generic(path: str, content: str, language: str) -> dict:
    loc = len([l for l in content.splitlines() if l.strip()])
    return {
        "path": path, "language": language, "loc": loc,
        "functions": [], "branches": 0, "loops": 0, "imports": [],
    }


def run_parser(files: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Her dosya icin parse dener. Hata veren dosyayi atlar.
    Returns: (parsed_files, skipped_files)
    """
    parsed, skipped = [], []
    for f in files:
        try:
            if f["language"] == "python":
                parsed.append(_stub_parse_python(f["path"], f["content"]))
            else:
                parsed.append(_stub_parse_generic(f["path"], f["content"], f["language"]))
        except Exception as exc:
            logger.warning("Parse hatasi atlandi: %s — %s", f["path"], exc)
            skipped.append({"path": f["path"], "error": str(exc)})
    return parsed, skipped


# ---------------------------------------------------------------------------
# Stub metrik motoru
# ---------------------------------------------------------------------------

def _estimate_cyclomatic(branches: int, loops: int) -> int:
    return 1 + branches + loops


def _estimate_halstead(loc: int, branches: int) -> float:
    return float(loc * 0.5 + branches * 2)


def run_metrics(parsed_files: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Parser ciktisından file ve function metrik listesi uretir.
    Returns: (file_metrics, function_metrics)
    """
    file_metrics, function_metrics = [], []
    for pf in parsed_files:
        cc = _estimate_cyclomatic(pf["branches"], pf["loops"])
        halstead = _estimate_halstead(pf["loc"], pf["branches"])

        file_metrics.append(build_file_entry(
            path=pf["path"], language=pf["language"],
            loc=pf["loc"], complexity_score=float(cc),
            dependency_count=len(pf["imports"]),
        ))

        for fn_name in pf["functions"]:
            function_metrics.append(build_function_entry(
                file_path=pf["path"], function_name=fn_name,
                cyclomatic_complexity=cc, halstead_score=halstead,
                loc=pf["loc"],
            ))

    return file_metrics, function_metrics


# ---------------------------------------------------------------------------
# Stub dependency analizi
# ---------------------------------------------------------------------------

def run_dependency_scan(parsed_files: list[dict]) -> list[dict]:
    """
    Import listesinden dosyalar arasi bagimlılık kenarlari cikarir.
    NetworkX entegrasyonu bu fonksiyonun ciktisini kullanacak.
    """
    path_index = {pf["path"] for pf in parsed_files}
    deps = []
    for pf in parsed_files:
        for imp in pf["imports"]:
            candidate = imp.replace(".", "/") + ".py"
            if candidate in path_index:
                deps.append(build_dependency_entry(
                    source_path=pf["path"],
                    target_path=candidate,
                    dependency_type="import",
                ))
    return deps


# ---------------------------------------------------------------------------
# Ana orkestrasyon fonksiyonu
# ---------------------------------------------------------------------------

def analyze_repo(
    run_id: UUID,
    project_id: UUID,
    repo_url: str,
    ref: str = "main",
) -> dict:
    """
    Uctan uca analiz akisi:
    1. Repo indir
    2. Parser calistir (hata veren dosyalar atlanir)
    3. Metrik hesapla
    4. Dependency tara
    5. Payload birlestir ve dondur
    """
    logger.info("Analiz basliyor: run_id=%s repo=%s ref=%s", run_id, repo_url, ref)
    timing: dict[str, float] = {}

    t0 = time.perf_counter()
    files = download_repo(repo_url, ref=ref)
    timing["download_sec"] = round(time.perf_counter() - t0, 3)
    logger.info("%d kaynak dosya indirildi (%.2fs)", len(files), timing["download_sec"])

    t0 = time.perf_counter()
    parsed, skipped = run_parser(files)
    timing["parsing_sec"] = round(time.perf_counter() - t0, 3)
    if skipped:
        logger.warning("%d dosya atlandı: %s", len(skipped), [s["path"] for s in skipped])

    t0 = time.perf_counter()
    file_metrics, function_metrics = run_metrics(parsed)
    timing["metrics_sec"] = round(time.perf_counter() - t0, 3)

    t0 = time.perf_counter()
    dependencies = run_dependency_scan(parsed)
    timing["dependency_sec"] = round(time.perf_counter() - t0, 3)

    timing["total_sec"] = round(sum(timing.values()), 3)

    content_blob = "".join(f["content"] for f in files)
    commit_hash = hashlib.sha1(content_blob.encode()).hexdigest()[:12]

    payload = build_analysis_payload(
        run_id=run_id, project_id=project_id,
        branch_name=ref, commit_hash=commit_hash,
        parser_version=PARSER_VERSION,
        files=file_metrics, functions=function_metrics,
        dependencies=dependencies,
    )

    payload["timing"] = timing
    payload["skipped_files"] = skipped
    payload["partial"] = len(skipped) > 0

    logger.info(
        "Analiz tamamlandi: %d dosya, %d fonksiyon, %d bagimlilik, %d atlandi | toplam %.2fs",
        len(file_metrics), len(function_metrics), len(dependencies),
        len(skipped), timing["total_sec"],
    )
    return payload
