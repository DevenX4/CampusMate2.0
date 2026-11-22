"""Stage 1: read text from the PDF, page by page, restricted to the version's page scope."""

from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader


@dataclass
class Page:
    number: int  # physical page number, 1-based (what citations use)
    lines: list[str] = field(default_factory=list)


def pages_in_scope(page_scope: dict | None) -> list[int] | None:
    """The union of all page lists in a scope such as
    {"PROG-BTECH-IT-001": [10, ..., 18], "PROG-MTECH-IT-001": [104, ..., 108]}; None = every page."""
    if not page_scope:
        return None
    return sorted({page for pages in page_scope.values() for page in pages})


def extract_pages(path: Path, only: list[int] | None = None) -> list[Page]:
    reader = PdfReader(path)
    numbers = only if only is not None else range(1, len(reader.pages) + 1)
    return [
        Page(number, (reader.pages[number - 1].extract_text() or "").splitlines())
        for number in numbers if 1 <= number <= len(reader.pages)
    ]
