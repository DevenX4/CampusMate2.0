"""Stage 3: split cleaned pages into chunks, following the document's own structure.

Rules:
- A new section starts at a heading: an entity heading ("COURSE-2CEIT602 — ..."), a numbered
  heading ("1.1.3 List of courses ..."), or a page whose known title differs from the
  previous page's (e.g. the next semester of the official syllabus).
- Lines are packed into chunks of at most `max_chars`, and a line is NEVER split across
  chunks, so a table row (one course with all its credits) always stays together. Only a
  single line longer than max_chars is cut, at sentence or word boundaries.
"""

import re
from dataclasses import dataclass, field

from app.ingestion.extract import Page

EM_DASH = chr(0x2014)
ENTITY_HEADING = re.compile(r"^(?:[A-Z]+-)+[A-Z0-9]+(?:-[A-Z0-9]+)* " + EM_DASH + " ")
# "1.1.3 List of courses": short numbers, then a word. Not a table row like "3.00 1.00 0/40 ...".
NUMBERED_HEADING = re.compile(r"^\d{1,2}(?:\.\d{1,2}){1,3}\s+[A-Za-z]")


@dataclass
class Chunk:
    text: str
    page_start: int
    page_end: int
    section: str | None


@dataclass
class _Section:
    title: str | None
    lines: list[tuple[int, str]] = field(default_factory=list)  # (page number, line)


def is_heading(line: str) -> bool:
    return bool(ENTITY_HEADING.match(line) or NUMBERED_HEADING.match(line))


def split_sections(pages: list[Page], page_titles: dict[int, str] | None = None) -> list[_Section]:
    page_titles = page_titles or {}
    sections: list[_Section] = []
    last_page_title: str | None = None
    for page in pages:
        page_title = page_titles.get(page.number)
        if page_title and page_title != last_page_title:  # e.g. the next semester's page
            sections.append(_Section(page_title))
            last_page_title = page_title
        for line in page.lines:
            if is_heading(line):
                sections.append(_Section(line[:200]))  # the heading line also stays in the text
            elif not sections:
                sections.append(_Section(page_title))
            sections[-1].lines.append((page.number, line))
    return [s for s in sections if s.lines]


def _split_long_line(line: str, max_chars: int) -> list[str]:
    """Cut an over-long line at sentence ends, falling back to word boundaries."""
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.;:!?])\s+", line):
        for word in sentence.split(" ") if len(sentence) > max_chars else [sentence]:
            candidate = f"{current} {word}".strip()
            if len(candidate) > max_chars and current:
                pieces.append(current)
                candidate = word
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def pack(section: _Section, max_chars: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    buffer: list[tuple[int, str]] = []

    def emit() -> None:
        if buffer:
            chunks.append(Chunk("\n".join(line for _, line in buffer), buffer[0][0], buffer[-1][0], section.title))
            buffer.clear()

    for page, line in section.lines:
        parts = _split_long_line(line, max_chars) if len(line) > max_chars else [line]
        for part in parts:
            size = sum(len(text) + 1 for _, text in buffer) + len(part)
            if size > max_chars:
                emit()
            buffer.append((page, part))
    emit()
    return chunks


def chunk_pages(pages: list[Page], max_chars: int, page_titles: dict[int, str] | None = None) -> list[Chunk]:
    return [chunk for section in split_sections(pages, page_titles) for chunk in pack(section, max_chars)]
