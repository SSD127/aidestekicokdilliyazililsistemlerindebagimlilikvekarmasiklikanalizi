import io
import zipfile
from pathlib import PurePosixPath
from urllib.parse import urlparse

import requests

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

MAX_FILE_SIZE_BYTES = 500_000
MAX_TOTAL_FILES = 300


class RepoTooLargeError(Exception):
    pass


def validate_github_repo_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return False
    path = parsed.path.strip("/")
    return len(path.split("/")) >= 2


def _extract_owner_repo(url: str) -> tuple[str, str]:
    path = urlparse(url).path.strip("/").split("/")
    return path[0], path[1]


def download_repo(repo_url: str, ref: str = "main") -> list[dict]:
    """
    GitHub reposunu zip olarak indirir, desteklenen kaynak dosyaları çıkarır.
    Returns: [{"path": str, "language": str, "content": str}, ...]
    Raises: RepoTooLargeError, requests.HTTPError
    """
    owner, repo = _extract_owner_repo(repo_url)
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{ref}.zip"

    response = requests.get(zip_url, timeout=30)
    if response.status_code == 404:
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
        response = requests.get(zip_url, timeout=30)
    response.raise_for_status()

    files: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        entries = [e for e in zf.infolist() if not e.is_dir()]
        if len(entries) > MAX_TOTAL_FILES * 10:
            raise RepoTooLargeError(
                f"Repo çok büyük: {len(entries)} dosya (max {MAX_TOTAL_FILES * 10})"
            )

        for entry in entries:
            suffix = PurePosixPath(entry.filename).suffix.lower()
            language = SUPPORTED_EXTENSIONS.get(suffix)
            if not language:
                continue
            if entry.file_size > MAX_FILE_SIZE_BYTES:
                continue

            # zip içindeki ilk klasör prefixini at (repo-main/ gibi)
            parts = entry.filename.split("/", 1)
            clean_path = parts[1] if len(parts) > 1 else entry.filename

            try:
                content = zf.read(entry.filename).decode("utf-8", errors="replace")
            except Exception:
                continue

            files.append({"path": clean_path, "language": language, "content": content})

            if len(files) >= MAX_TOTAL_FILES:
                break

    return files
