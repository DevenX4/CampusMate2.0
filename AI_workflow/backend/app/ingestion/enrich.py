"""Stage 4: give every chunk the metadata that retrieval and citations need.

- entity_ids: known IDs mentioned in the text (COURSE-2CEIT602, FAC-IT-003, ...), and course
  codes as printed in official tables (2CEIT602 -> COURSE-2CEIT602);
- source_type: the chunk's trust level (see chunk_source_type);
- program/semester: from IDs in the text and, for official pages, from the semesters table,
  whose provenance says which page each semester is printed on.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.curriculum import Program, Semester

ENTITY_ID = re.compile(
    r"\b(?:COURSE|FAC|LAB|FCL|POLICY|NOTICE|FAQ|CAL|PROG|SEM|DEPT|RA|ROOM|BLDG|EGRP|OFF|GRADE|TA"
    r"|PREREQ|DQ|UNIV|SCHOOL|COLLEGE|DOC)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b"
)
COURSE_CODE = re.compile(r"\b[0-9][A-Z]{2,6}[0-9][A-Z0-9]*\b")  # 2CEIT602, 2HS6101, 3IT101

# Trust labels that the synthetic PDFs print: "[O]", "[DO]", "[S]" on field lines, and
# "source_type: synthetic" under entity headings.
_MARKERS = {"O": "official", "DO": "derived_official", "S": "synthetic"}
_MARKER = re.compile(r"\[(O|DO|S)\]")
_SOURCE_LINE = re.compile(r"source_type: (official|derived_official|synthetic)\b")


def find_entity_ids(text: str, known_ids: set[str]) -> list[str]:
    ids = {m for m in ENTITY_ID.findall(text) if m in known_ids}
    ids |= {f"COURSE-{code}" for code in COURSE_CODE.findall(text) if f"COURSE-{code}" in known_ids}
    return sorted(ids)


def chunk_source_type(text: str, document_source_type: str) -> tuple[str, list[str]]:
    """Returns (source_type, labels found in the text).

    - Text from an official GUNI PDF is 'official'.
    - Text from a synthetic PDF is 'synthetic' if it contains anything synthetic (or no labels
      at all). If it only restates facts labelled official/derived, it is 'derived_official':
      a demo document is never itself an official source, even when it quotes one. Answers
      should cite the official PDF for such facts.
    """
    labels = {_MARKERS[m] for m in _MARKER.findall(text)} | set(_SOURCE_LINE.findall(text))
    if document_source_type == "official":
        return "official", sorted(labels)
    if "synthetic" in labels or not labels:
        return "synthetic", sorted(labels)
    return "derived_official", sorted(labels)


@dataclass
class PageContext:
    title: str
    program_id: str
    semester_id: str


def official_page_context(db: Session, document_id: str, version_no: int) -> dict[int, PageContext]:
    """Page -> semester for pages that the semesters table cites as its source, e.g. syllabus
    page 15 -> 'B.TECH-IT Semester VI'. Empty for documents no semester cites."""
    rows = db.execute(
        select(Semester, Program.short_name).join(Program)
        .where(Semester.source_document_id == document_id, Semester.source_version_no == version_no)
    ).all()
    context: dict[int, PageContext] = {}
    for semester, program_short_name in rows:
        for page in range(semester.source_page, (semester.source_page_end or semester.source_page) + 1):
            context[page] = PageContext(f"{program_short_name} {semester.semester_name}",
                                        semester.program_id, semester.semester_id)
    return context
