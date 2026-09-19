"""Step 1 of seeding: read the canonical dataset files and clean individual values.

Nothing here touches the database.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.services.storage import sha256_of

# Tables in data/structured/ that are loaded. relationships.json is deliberately absent:
# edges are derived from the relational data, and that file is kept as a test oracle.
TABLES = (
    "university", "org_units", "departments", "research_areas", "buildings", "rooms",
    "faculty", "programs", "semesters", "courses", "elective_groups", "course_offerings",
    "course_prerequisites", "grading_scheme", "data_quality_conflicts", "laboratories",
    "facilities", "teaching_assignments", "policies", "academic_calendar", "notices", "faq",
)

# UTF-8 text wrongly decoded as Windows-1252 shows these tell-tale sequences,
# e.g. an en dash (U+2013, UTF-8 bytes E2 80 93) turns into 3 characters: U+00E2 U+20AC U+201C.
_MOJIBAKE_MARKERS = ("\u00e2\u20ac", "\u00c3", "\u00c2")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class TextRepairs:
    """Counts every garbled string that was repaired, and remembers what changed."""

    count: int = 0
    examples: list[tuple[str, str]] = field(default_factory=list)

    def repair(self, value: str) -> str:
        if not has_mojibake(value):
            return value
        try:
            fixed = value.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value  # not the cp1252 round-trip pattern: leave it untouched
        self.count += 1
        self.examples.append((value, fixed))
        return fixed

    def clean(self, obj: Any) -> Any:
        """Repair every string inside a JSON value (dicts and lists included)."""
        if isinstance(obj, str):
            return self.repair(obj)
        if isinstance(obj, list):
            return [self.clean(v) for v in obj]
        if isinstance(obj, dict):
            return {k: self.clean(v) for k, v in obj.items()}
        return obj


def has_mojibake(value: str) -> bool:
    return any(marker in value for marker in _MOJIBAKE_MARKERS)


def parse_iso_date(value: str | None) -> date | None:
    """'2026-07-01' -> date. Anything less exact, such as
    '2021-06-01 (Effective Year 2021-2022; exact date not stated)', -> None: we never
    turn an approximate date into a precise one."""
    if value is None or not _ISO_DATE.fullmatch(value):
        return None
    return date.fromisoformat(value)


def parse_dmy_date(value: str | None) -> date | None:
    """'28/09/2022' (as printed on the syllabus) -> date(2022, 9, 28)."""
    return None if value is None else datetime.strptime(value, "%d/%m/%Y").date()


@dataclass
class DocumentFile:
    """A registered PDF on disk, verified against the SHA-256 in the registry."""

    path: Path
    sha256: str
    size_bytes: int


@dataclass
class SourceData:
    tables: dict[str, list[dict]]
    registry: list[dict]
    # (document_id, entity_id) -> pages where the entity appears, from entity_index.json
    index_pages: dict[tuple[str, str], set[int]]
    files: dict[str, DocumentFile]  # document_id -> verified file
    repairs: TextRepairs


def _records(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else next(v for v in data.values() if isinstance(v, list))


def load_source(data_dir: Path) -> SourceData:
    repairs = TextRepairs()
    tables = {name: repairs.clean(_records(data_dir / "structured" / f"{name}.json")) for name in TABLES}
    registry = repairs.clean(_records(data_dir / "registry" / "document_registry.json"))

    index_pages: dict[tuple[str, str], set[int]] = {}
    entity_index = json.loads((data_dir / "registry" / "entity_index.json").read_text(encoding="utf-8"))
    for entity in entity_index["entities"].values():  # a dict keyed by entity_id
        for rep in entity["representations"]:
            if rep["representation"] in ("pdf", "official_pdf"):
                index_pages.setdefault((rep["document_id"], entity["entity_id"]), set()).add(rep["page"])

    return SourceData(tables, registry, index_pages, verify_files(data_dir / "pdfs", registry), repairs)


def verify_files(pdf_dir: Path, registry: list[dict]) -> dict[str, DocumentFile]:
    """Every registered PDF must exist and match its registry SHA-256 exactly.
    Files live in data/pdfs/<source_type>/<filename>, as listed in data/pdfs.sha256."""
    files = {}
    for doc in registry:
        path = pdf_dir / doc["source_type"] / doc["filename"]
        if not path.is_file():
            raise FileNotFoundError(f"{doc['document_id']}: {path} is missing (see README > PDFs)")
        expected = doc["file_hash"].removeprefix("sha256:")
        actual = sha256_of(path)
        if actual != expected:
            raise ValueError(f"{doc['document_id']}: {path.name} sha256 {actual} != registry {expected}")
        files[doc["document_id"]] = DocumentFile(path, actual, path.stat().st_size)
    return files
