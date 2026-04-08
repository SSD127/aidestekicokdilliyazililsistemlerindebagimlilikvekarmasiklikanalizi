"""
github_pipeline.py — GitHub Repo İndirme ve URL Doğrulama Servisi

Bu dosya bir GitHub reposunu zip olarak indirip desteklenen kaynak kod
dosyalarını çıkaran servisi içerir.
Analiz orkestratörü (orchestrator.py) bu servisi çağırarak ham dosya içeriklerini alır.

Desteklenen diller: Python, Java, JavaScript, TypeScript, C, C++
"""

import io
import zipfile
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests

# Hangi uzantının hangi dile karşılık geldiği eşlemesi
SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
}

# Tek dosya için maksimum boyut — çok büyük dosyalar analizi yavaşlatır
MAX_FILE_SIZE_BYTES = 500_000

# Analize alınacak maksimum dosya sayısı — NFR-1 performans hedefi için
MAX_TOTAL_FILES = 300


class RepoTooLargeError(Exception):
    # Repo boyutu sınırı aşınca fırlatılır; orchestrator bunu yakalar ve run'ı failed yapar
    pass


def validate_github_repo_url(url: str) -> bool:
    # Girilen URL'nin geçerli bir GitHub repo adresi olup olmadığını kontrol eder
    # Beklenen format: https://github.com/owner/repo
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return False
    path = parsed.path.strip("/")
    return len(path.split("/")) >= 2


def _extract_owner_repo(url: str) -> tuple[str, str]:
    # URL'den owner ve repo adını ayrıştırır
    path = urlparse(url).path.strip("/").split("/")
    return path[0], path[1]


def download_repo(repo_url: str, ref: str = "main") -> list[dict]:
    """
    GitHub reposunu zip olarak indirir ve desteklenen kaynak dosyalarını döndürür.

    Args:
        repo_url: GitHub repo URL'si (örn. https://github.com/owner/repo)
        ref: İndirilecek branch veya tag (varsayılan: main)

    Returns:
        [{"path": str, "language": str, "content": str}, ...]
        Her eleman bir kaynak dosyayı ve içeriğini temsil eder.

    Raises:
        RepoTooLargeError: Dosya sayısı MAX_TOTAL_FILES * 10'u aşarsa
        requests.HTTPError: GitHub'dan hatalı HTTP cevabı gelirse
    """
    owner, repo = _extract_owner_repo(repo_url)

    # Önce istenen branch'i dene, 404 gelirse master'ı dene
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{ref}.zip"
    response = requests.get(zip_url, timeout=30)
    if response.status_code == 404:
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
        response = requests.get(zip_url, timeout=30)
    response.raise_for_status()

    files: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        entries = [e for e in zf.infolist() if not e.is_dir()]

        # Aşırı büyük repo kontrolü
        if len(entries) > MAX_TOTAL_FILES * 10:
            raise RepoTooLargeError(
                f"Repo cok buyuk: {len(entries)} dosya (max {MAX_TOTAL_FILES * 10})"
            )

        for entry in entries:
            # Desteklenmeyen uzantıları atla
            suffix = PurePosixPath(entry.filename).suffix.lower()
            language = SUPPORTED_EXTENSIONS.get(suffix)
            if not language:
                continue

            # Çok büyük dosyaları atla
            if entry.file_size > MAX_FILE_SIZE_BYTES:
                continue

            # Zip içindeki ilk klasör prefixini temizle (örn. repo-main/ → doğrudan yol)
            parts = entry.filename.split("/", 1)
            clean_path = parts[1] if len(parts) > 1 else entry.filename

            try:
                content = zf.read(entry.filename).decode("utf-8", errors="replace")
            except Exception:
                continue

            files.append({"path": clean_path, "language": language, "content": content})

            # Maksimum dosya sınırına ulaşınca dur
            if len(files) >= MAX_TOTAL_FILES:
                break

    return files
