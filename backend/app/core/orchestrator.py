"""
orchestrator.py — Ana Analiz Orkestratörü

PolyMetric'in uçtan uca analiz akışını yöneten modül.
GitHub'dan repo indirir, Tree-sitter parser'ını çalıştırır, McCabe ve Halstead
metriklerini hesaplar, dosyalar arası bağımlılıkları çıkarır ve tüm sonuçları
analysis_result.schema.json formatında tek payload olarak birleştirir.

Akış:
  1. download_repo()           → GitHub'dan zip indir, kaynak dosyaları çıkar
  2. run_parser()              → Her dosyayı parser.parse_file() ile tree-sitter AST'sine çevir
  3. run_metrics()             → Parser çıktısından per-function McCabe + Halstead Effort üret
  4. run_dependency_scan()     → Parser'ın tespit ettiği import'lardan dosyalar arası bağımlılık çıkar
  5. build_analysis_payload()  → Tüm sonuçları AnalysisResult formatında birleştir
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from pathlib import PurePosixPath
from uuid import UUID

from app.core.parser import (
    PARSER_VERSION as PARSER_LIB_VERSION,
    get_grammar_version_summary,
    parse_file,
)
from app.core.payload_builder import (
    build_analysis_payload,
    build_dependency_entry,
    build_file_entry,
    build_function_entry,
)
from app.services.github_pipeline import download_repo

logger = logging.getLogger(__name__)

# Run metadata'sına yazılacak parser sürümü; parser.py modülüyle aynı kaynaktan gelir
PARSER_VERSION = PARSER_LIB_VERSION


def _is_test_file(path: str) -> bool:
    """Basename `test_*.py` veya `*_test.py` ise True (include_tests=False kapsamı)."""
    name = PurePosixPath(path).name
    if not name.endswith(".py"):
        return False
    return name.startswith("test_") or name.endswith("_test.py")


# ---------------------------------------------------------------------------
# Faz 2: Parser çalıştırma — tree-sitter tabanlı parser.parse_file() köprüsü
# ---------------------------------------------------------------------------

def run_parser(files: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Dosya listesini parser.parse_file() ile parse eder.

    Args:
        files: [{"path": str, "language": str, "content": str}, ...]

    Returns:
        (parsed_files, skipped_files)
        parsed_files: parser_ast.schema.json v1.1 yapısında dict listesi
        skipped_files: [{"path": str, "error": str}, ...]
    """
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


# ---------------------------------------------------------------------------
# Faz 3: Metrik hesaplama — gerçek McCabe ve Halstead Effort
# ---------------------------------------------------------------------------

def _halstead_effort(
    unique_operators: int,
    total_operators: int,
    unique_operands: int,
    total_operands: int,
) -> float:
    """
    Halstead Effort = D * V hesaplar.

    n = n1 + n2 (vocabulary), N = N1 + N2 (length)
    V = N * log2(n)
    D = (n1 / 2) * (N2 / n2)
    E = D * V
    Sıfıra bölme veya log2(0) durumlarında 0.0 döner.
    """
    n1, N1 = unique_operators, total_operators
    n2, N2 = unique_operands, total_operands
    n = n1 + n2
    N = N1 + N2
    if n <= 1 or n2 == 0:
        return 0.0
    volume = N * math.log2(n)
    difficulty = (n1 / 2.0) * (N2 / n2)
    return difficulty * volume


def _mccabe(branch_count: int, loop_count: int) -> int:
    # McCabe Cyclomatic Complexity = 1 + karar noktaları (branch + loop)
    return 1 + branch_count + loop_count


def run_metrics(parsed_files: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Parser çıktısından dosya ve fonksiyon düzeyinde metrik listeleri üretir.

    Per-function:
      - cyclomatic_complexity: 1 + branch_count + loop_count
      - halstead_score: gerçek Effort = D * V
      - loc: executable_lines
      - start_line/end_line: location'dan
      - risk_score: payload_builder.build_function_entry içinde risk.calculate_risk_level ile

    Per-file:
      - complexity_score: dosyadaki tüm fonksiyonların CC toplamı
      - loc: summary.loc_code
      - dependency_count: summary.import_count

    Returns:
        (file_metrics, function_metrics)
    """
    file_metrics: list[dict] = []
    function_metrics: list[dict] = []

    for pf in parsed_files:
        path = pf["file_path"]
        language = pf.get("language", "python")
        summary = pf.get("summary", {})
        functions = pf.get("functions", [])

        # Her fonksiyon için gerçek metrikleri hesapla
        file_cc_total = 0.0
        for fn in functions:
            cc = _mccabe(fn.get("branch_count", 0), fn.get("loop_count", 0))
            effort = _halstead_effort(
                unique_operators=fn.get("unique_operators", 0),
                total_operators=fn.get("total_operators", 0),
                unique_operands=fn.get("unique_operands", 0),
                total_operands=fn.get("total_operands", 0),
            )
            location = fn.get("location", {}) or {}
            function_metrics.append(build_function_entry(
                file_path=path,
                function_name=fn.get("name", "<anonymous>"),
                cyclomatic_complexity=cc,
                halstead_score=effort,
                loc=fn.get("executable_lines", 0),
                start_line=max(int(location.get("start_line", 1) or 1), 1),
                end_line=max(int(location.get("end_line", 1) or 1), 1),
            ))
            file_cc_total += cc

        # Dosya düzeyinde metrik — fonksiyonlardan agrege edilir
        file_metrics.append(build_file_entry(
            path=path,
            language=language,
            loc=summary.get("loc_code", 0),
            complexity_score=float(file_cc_total),
            dependency_count=summary.get("import_count", 0),
        ))

    return file_metrics, function_metrics


# ---------------------------------------------------------------------------
# Faz 4: Bağımlılık taraması — parser.imports[] dict listesinden grafik üret
# ---------------------------------------------------------------------------

def run_dependency_scan(parsed_files: list[dict]) -> list[dict]:
    """
    Parser'ın çıkardığı import kayıtlarından dosyalar arası bağımlılık kenarları üretir.
    Sadece repo içindeki dosyalara işaret eden import'lar dahil edilir.

    parser.py imports[] formatı:
        {"kind": "import"|"from_import", "module": "...", "raw_text": "...", "location": {...}}
    """
    path_index = {pf["file_path"] for pf in parsed_files}
    deps: list[dict] = []
    for pf in parsed_files:
        source_path = pf["file_path"]
        for imp in pf.get("imports", []):
            module = imp.get("module") if isinstance(imp, dict) else None
            if not module or module == "?":
                continue
            # "utils.helper" → "utils/helper.py" dönüşümü
            candidate = module.replace(".", "/") + ".py"
            if candidate in path_index:
                deps.append(build_dependency_entry(
                    source_path=source_path,
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
    include_tests: bool = True,
) -> dict:
    """
    Uçtan uca analiz akışını yönetir ve AnalysisResult payload'ını döndürür.
    Hata durumunda exception fırlatır; çağıran katman run'ı failed olarak işaretler.
    """
    logger.info("Analiz basliyor: run_id=%s repo=%s ref=%s", run_id, repo_url, ref)
    timing: dict[str, float] = {}

    # 1. Repo'yu indir
    t0 = time.perf_counter()
    files = download_repo(repo_url, ref=ref)
    timing["download_sec"] = round(time.perf_counter() - t0, 3)
    logger.info("%d kaynak dosya indirildi (%.2fs)", len(files), timing["download_sec"])

    if not include_tests:
        before = len(files)
        files = [f for f in files if not _is_test_file(f["path"])]
        logger.info("include_tests=False: %d test dosyasi haric, %d dosya kaldi", before - len(files), len(files))

    # 2. Parse
    t0 = time.perf_counter()
    parsed, skipped = run_parser(files)
    timing["parsing_sec"] = round(time.perf_counter() - t0, 3)
    if skipped:
        logger.warning("%d dosya atlandi", len(skipped))

    # 3. Metrik hesaplama
    t0 = time.perf_counter()
    file_metrics, function_metrics = run_metrics(parsed)
    timing["metrics_sec"] = round(time.perf_counter() - t0, 3)

    # 4. Bağımlılık taraması
    t0 = time.perf_counter()
    dependencies = run_dependency_scan(parsed)
    timing["dependency_sec"] = round(time.perf_counter() - t0, 3)

    timing["total_sec"] = round(sum(timing.values()), 3)

    # 5. Commit hash — gerçek hash yoksa içerik blob'undan SHA1 türetilir
    content_blob = "".join(f["content"] for f in files)
    commit_hash = hashlib.sha1(content_blob.encode()).hexdigest()[:12]

    # 6. AnalysisResult formatında birleştir
    payload = build_analysis_payload(
        run_id=run_id,
        project_id=project_id,
        branch_name=ref,
        commit_hash=commit_hash,
        parser_version=PARSER_VERSION,
        grammar_version=get_grammar_version_summary(pf.get("language", "") for pf in parsed),
        files=file_metrics,
        functions=function_metrics,
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
