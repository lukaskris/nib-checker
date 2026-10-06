"""PDF basics: page count + raw text."""
from pathlib import Path

from pypdf import PdfReader


def extract(path: str | Path) -> dict:
    r = PdfReader(str(path))
    pages = [p.extract_text() or "" for p in r.pages]
    return {
        "page_count": len(pages),
        "full_text": "\n".join(pages),
        "title": (r.metadata or {}).get("/Title", "") or "",
    }
