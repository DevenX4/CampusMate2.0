"""Stage 2: clean extracted text.

- repair UTF-8 text that was decoded as Windows-1252 (the same repair the seed uses);
- normalise whitespace and drop empty lines;
- remove boilerplate: running headers and footers (such as "Page 7" or the synthetic-data
  banner). A line counts as boilerplate only if the same text sits at the same position near
  the top or bottom (line 1, 2, ... or last, second-to-last, ...) on most pages. Structured
  documents also repeat their field labels ("faculty [S]") on every page, but those move
  around with the content, and they (with their trust markers) must be kept.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from app.ingestion.extract import Page
from app.seed.source import TextRepairs

BOILERPLATE_SHARE = 0.6  # a line on at least 60% of pages is boilerplate...
BOILERPLATE_MIN_PAGES = 3  # ...but only judge that when there are enough pages
HEADER_LINES, FOOTER_LINES = 4, 3  # where running headers and footers can be
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")


@dataclass
class CleanResult:
    pages: list[Page]
    removed_boilerplate: list[str] = field(default_factory=list)
    repaired_strings: int = 0


def _pattern(line: str) -> str:
    return _DIGITS.sub("#", line)  # "Page 7" and "Page 8" are the same boilerplate


def _edge_keys(lines: list[str]) -> list[tuple[int, str]]:
    """(position, pattern) for the header and footer lines: positions 0, 1, ... from the top
    and -1, -2, ... from the bottom. The two windows never overlap on short pages."""
    top = range(min(HEADER_LINES, len(lines)))
    bottom = range(max(HEADER_LINES, len(lines) - FOOTER_LINES), len(lines))
    return [(i, _pattern(lines[i])) for i in top] + [(i - len(lines), _pattern(lines[i])) for i in bottom]


def clean_pages(pages: list[Page]) -> CleanResult:
    repairs = TextRepairs()
    cleaned = [
        Page(p.number, [line for line in (_SPACES.sub(" ", repairs.repair(raw)).strip() for raw in p.lines) if line])
        for p in pages
    ]
    boilerplate: set[str] = set()
    if len(cleaned) >= BOILERPLATE_MIN_PAGES:
        seen = Counter(key for p in cleaned for key in set(_edge_keys(p.lines)))
        boilerplate = {key for key, count in seen.items() if count / len(cleaned) >= BOILERPLATE_SHARE}
    for page in cleaned:
        drop = {i if i >= 0 else i + len(page.lines) for i, pattern in _edge_keys(page.lines)
                if (i, pattern) in boilerplate}
        page.lines = [line for i, line in enumerate(page.lines) if i not in drop]
    return CleanResult(cleaned, sorted({pattern for _, pattern in boilerplate}), repairs.count)
