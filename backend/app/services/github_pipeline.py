from urllib.parse import urlparse


def validate_github_repo_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc not in {"github.com", "www.github.com"}:
        return False
    path = parsed.path.strip("/")
    # owner/repo beklenir.
    return len(path.split("/")) >= 2
