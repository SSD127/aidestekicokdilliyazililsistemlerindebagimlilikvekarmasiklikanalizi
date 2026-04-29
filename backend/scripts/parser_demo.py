"""
parser_demo.py — parser.py modulunun ornek kullanimi

Tek bir Python dosyasini parse edip parser_ast.schema.json v1.1.0
formatinda JSON ciktisini stdout'a basar.

Kullanim:
    python -m backend.scripts.parser_demo path/to/file.py
    python backend/scripts/parser_demo.py            # ornek inline kod
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Backend root'unu sys.path'e ekleyerek "from app.core.parser" import edebilelim
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.parser import build_payload  # noqa: E402

DEMO_SOURCE = """
def merhaba(isim):
    if not isim:
        return "Misafir"
    for ch in isim:
        if ch.isspace():
            return "Bosluk var"
    return "Hosgeldin " + isim


def topla(a, b):
    return a + b
""".strip()


def _run_demo() -> None:
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        content = target.read_text(encoding="utf-8")
        files = [{"path": str(target), "language": "python", "content": content}]
    else:
        files = [{"path": "demo.py", "language": "python", "content": DEMO_SOURCE}]

    payload = build_payload(
        repo_url="https://github.com/example/parser-demo",
        ref="main",
        files=files,
    )

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _run_demo()
