"""
orchestrator.py — Ana Analiz Orkestratörü

Bu dosya PolyMetric'in en kritik modülüdür.
GitHub'dan repo indirmek, parse etmek, metrik hesaplamak, bağımlılık taramak
ve sonuçları birleştirmek gibi adımları sırayla koordine eder.

Orkestrasyon akışı:
  1. download_repo()      → GitHub'dan zip indir, kaynak dosyaları çıkar
  2. run_parser()         → Her dosyayı parse et, fonksiyon/branch/loop say
  3. run_metrics()        → Parse çıktısından complexity ve Halstead tahmini üret
  4. run_dependency_scan()→ Import ifadelerinden dosyalar arası bağımlılık çıkar
  5. build_analysis_payload() → Tüm sonuçları tek payload'da birleştir

NOT: run_parser(), run_metrics() ve run_dependency_scan() şu an stub implementasyon
içeriyor. Tree-sitter parser ve gerçek metrik motoru eklendiğinde bu fonksiyonlar
aynı arayüzü koruyarak gerçek implementasyonla değiştirilecektir.
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

# Hangi parser sürümünün kullanıldığını run metadata'sına yazar
PARSER_VERSION = "stub:v0.1"


# ---------------------------------------------------------------------------
# Stub parser — tree-sitter entegre edilene kadar regex tabanlı analiz
# ---------------------------------------------------------------------------

def _stub_parse_python(path: str, content: str) -> dict:
    """
    Python dosyaları için basit regex tabanlı parse.
    Gerçek tree-sitter parser geldiğinde bu fonksiyon değiştirilecektir.
    Döndürdüğü format parser modülüyle aynı olmalı.
    """
    lines = content.splitlines()
    # Boş ve yorum satırlarını hariç tutarak gerçek kod satırı say
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
    # Fonksiyon tanımlarını yakala (async def dahil)
    functions = re.findall(r"^\s*(?:async\s+)?def\s+(\w+)", content, re.MULTILINE)
    # Import ifadelerini yakala
    imports = re.findall(r"^\s*(?:import|from)\s+([\w.]+)", content, re.MULTILINE)
    # Karar noktalarını say
    branches = len(re.findall(r"\b(?:if|elif|else|except|case)\b", content))
    # Döngüleri say
    loops = len(re.findall(r"\b(?:for|while)\b", content))
    return {
        "path": path, "language": "python", "loc": loc,
        "functions": functions, "branches": branches,
        "loops": loops, "imports": imports,
    }


def _stub_parse_generic(path: str, content: str, language: str) -> dict:
    # Python dışı diller için minimal stub — sadece satır sayısı hesaplar
    loc = len([l for l in content.splitlines() if l.strip()])
    return {
        "path": path, "language": language, "loc": loc,
        "functions": [], "branches": 0, "loops": 0, "imports": [],
    }


def run_parser(files: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Dosya listesini parse eder; hata veren dosyaları atlar, listeye ekler.

    Args:
        files: [{"path": str, "language": str, "content": str}, ...]

    Returns:
        (parsed_files, skipped_files)
        skipped_files: [{"path": str, "error": str}, ...]
    """
    parsed, skipped = [], []
    for f in files:
        try:
            if f["language"] == "python":
                parsed.append(_stub_parse_python(f["path"], f["content"]))
            else:
                parsed.append(_stub_parse_generic(f["path"], f["content"], f["language"]))
        except Exception as exc:
            # Parse hatası tüm analizi durdurmaz; sadece o dosya atlanır
            logger.warning("Parse hatasi atlandi: %s — %s", f["path"], exc)
            skipped.append({"path": f["path"], "error": str(exc)})
    return parsed, skipped


# ---------------------------------------------------------------------------
# Stub metrik motoru — gerçek McCabe/Halstead gelene kadar tahmin üretir
# ---------------------------------------------------------------------------

def _estimate_cyclomatic(branches: int, loops: int) -> int:
    # McCabe CC tahmini: 1 (temel yol) + karar noktaları
    return 1 + branches + loops


def _estimate_halstead(loc: int, branches: int) -> float:
    # Basit Halstead effort tahmini; gerçek implementasyon parser ekibinden gelecek
    return float(loc * 0.5 + branches * 2)


def run_metrics(parsed_files: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Parser çıktısından dosya ve fonksiyon metrik listesi üretir.

    Returns:
        (file_metrics, function_metrics)
        Her dosya için complexity/loc/dependency,
        her fonksiyon için cyclomatic/halstead/risk_score hesaplanır.
    """
    file_metrics, function_metrics = [], []
    for pf in parsed_files:
        cc = _estimate_cyclomatic(pf["branches"], pf["loops"])
        halstead = _estimate_halstead(pf["loc"], pf["branches"])

        # Dosya düzeyinde metrik
        file_metrics.append(build_file_entry(
            path=pf["path"], language=pf["language"],
            loc=pf["loc"], complexity_score=float(cc),
            dependency_count=len(pf["imports"]),
        ))

        # Fonksiyon düzeyinde metrik — aynı dosyadaki tüm fonksiyonlar için
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
    Import ifadelerinden dosyalar arası bağımlılık kenarları çıkarır.
    NetworkX entegrasyonu bu fonksiyonun çıktısını kullanarak döngüsel bağımlılık
    tespiti ve modül kümesi görselleştirmesi yapacaktır.

    Örnek: "from utils import x" → source: current_file.py → target: utils.py
    """
    # Analiz edilen tüm dosya yollarını hızlı arama için sete al
    path_index = {pf["path"] for pf in parsed_files}
    deps = []
    for pf in parsed_files:
        for imp in pf["imports"]:
            # "utils.helper" → "utils/helper.py" dönüşümü
            candidate = imp.replace(".", "/") + ".py"
            # Sadece repo içindeki dosyalara olan bağımlılıkları kaydet
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
    Uçtan uca analiz akışını yönetir ve analiz sonuç payload'ını döndürür.

    Bu fonksiyon main.py'deki _run_analysis_background tarafından
    arka planda çağrılır. Hata durumunda exception fırlatır, çağıran
    run'ı failed olarak işaretler.

    Args:
        run_id: Devam eden analiz run'ının UUID'si
        project_id: Run'ın bağlı olduğu proje UUID'si
        repo_url: Analiz edilecek GitHub repo URL'si
        ref: Branch veya tag adı

    Returns:
        analysis_result.schema.json formatında payload dict
    """
    logger.info("Analiz basliyor: run_id=%s repo=%s ref=%s", run_id, repo_url, ref)
    timing: dict[str, float] = {}

    # 1. Repo'yu indir ve kaynak dosyaları çıkar
    t0 = time.perf_counter()
    files = download_repo(repo_url, ref=ref)
    timing["download_sec"] = round(time.perf_counter() - t0, 3)
    logger.info("%d kaynak dosya indirildi (%.2fs)", len(files), timing["download_sec"])

    # 2. Parse — hatalı dosyalar atlanır, analiz devam eder
    t0 = time.perf_counter()
    parsed, skipped = run_parser(files)
    timing["parsing_sec"] = round(time.perf_counter() - t0, 3)
    if skipped:
        logger.warning("%d dosya atlandi: %s", len(skipped), [s["path"] for s in skipped])

    # 3. Metrik hesaplama
    t0 = time.perf_counter()
    file_metrics, function_metrics = run_metrics(parsed)
    timing["metrics_sec"] = round(time.perf_counter() - t0, 3)

    # 4. Bağımlılık taraması
    t0 = time.perf_counter()
    dependencies = run_dependency_scan(parsed)
    timing["dependency_sec"] = round(time.perf_counter() - t0, 3)

    timing["total_sec"] = round(sum(timing.values()), 3)

    # 5. Gerçek commit hash yoksa dosya içeriklerinden SHA1 üret
    content_blob = "".join(f["content"] for f in files)
    commit_hash = hashlib.sha1(content_blob.encode()).hexdigest()[:12]

    # 6. Tüm sonuçları tek payload'da birleştir
    payload = build_analysis_payload(
        run_id=run_id, project_id=project_id,
        branch_name=ref, commit_hash=commit_hash,
        parser_version=PARSER_VERSION,
        files=file_metrics, functions=function_metrics,
        dependencies=dependencies,
    )

    # Performans ve kısmi analiz bilgisini payload'a ekle
    payload["timing"] = timing
    payload["skipped_files"] = skipped
    payload["partial"] = len(skipped) > 0

    logger.info(
        "Analiz tamamlandi: %d dosya, %d fonksiyon, %d bagimlilik, %d atlandi | toplam %.2fs",
        len(file_metrics), len(function_metrics), len(dependencies),
        len(skipped), timing["total_sec"],
    )
    return payload
