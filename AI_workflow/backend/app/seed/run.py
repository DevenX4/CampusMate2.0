"""Seeding orchestration: read -> transform -> write (in foreign-key order) -> validate.

The caller owns the transaction: it commits only if `SeedReport.problems` is empty.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Base
from app.seed.consistency import check_consistency
from app.seed.source import SourceData, load_source
from app.seed.transform import build_rows
from app.seed.validate import DOCUMENT_TABLES, validate
from app.seed.writer import TableStats, write
from app.services.storage import store_original

# Documents and their versions are only ever inserted by the seed: once registered, their
# status belongs to the admin (Phase 6), and re-running the seed must not undo admin actions.
INSERT_ONLY = {"documents", "document_versions"}
# Pure link tables and document_entities are rewritten to match the dataset exactly.
SYNC = {"lab_courses", "faculty_research_areas", "grade_band_programs", "policy_links",
        "notice_links", "faq_links", "calendar_event_semesters", "document_entities"}


@dataclass
class SeedReport:
    tables: list[TableStats]
    problems: list[str]
    text_repairs: list[tuple[str, str]]
    source_types: Counter = field(default_factory=Counter)
    files_stored: int = 0

    def render(self) -> str:
        lines = [f"{'table':28} {'rows':>6} {'inserted':>9} {'updated':>8} {'unchanged':>10} {'deleted':>8}"]
        for s in self.tables:
            lines.append(f"{s.table:28} {s.rows:6} {s.inserted:9} {s.updated:8} {s.unchanged:10} {s.deleted:8}")
        total = sum(s.rows for s in self.tables)
        lines.append(f"{len(self.tables)} tables, {total} rows | files stored: {self.files_stored}")
        lines.append("facts by source_type: " + ", ".join(f"{k}={v}" for k, v in sorted(self.source_types.items())))
        lines.append(f"garbled text repaired: {len(self.text_repairs)}")
        # !a = escaped ASCII, so the change is readable in any terminal encoding.
        lines += [f"  {before!a} -> {after!a}" for before, after in self.text_repairs]
        lines.append("validation: " + ("OK" if not self.problems else f"{len(self.problems)} PROBLEM(S)"))
        lines += [f"  - {p}" for p in self.problems]
        return "\n".join(lines)


def seed(session: Session, data_dir: Path, storage_dir: Path | None) -> SeedReport:
    """Load the dataset. storage_dir=None skips copying PDFs into storage (dry runs)."""
    src: SourceData = load_source(data_dir)
    rows = build_rows(src)
    seeded_docs = [d["document_id"] for d in rows["documents"]]

    stats = []
    # sorted_tables = parents before children, so every foreign key target already exists.
    for table in Base.metadata.sorted_tables:
        if table.name not in rows:
            continue
        mode = "insert_only" if table.name in INSERT_ONLY else "sync" if table.name in SYNC else "upsert"
        scope = table.c.document_id.in_(seeded_docs) if table.name in DOCUMENT_TABLES else None
        stats.append(write(session, table, rows[table.name], mode, scope))

    # Check the deferred foreign keys now (not at COMMIT) so violations become validation errors.
    session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    problems = validate(session, src, rows) + check_consistency(session, src)

    stored = 0
    if storage_dir is not None and not problems:
        for file in src.files.values():
            store_original(storage_dir, file.path, file.sha256)
            stored += 1

    source_types = Counter(  # facts only: rows that cite a document, not the documents themselves
        r["source_type"] for name, table_rows in rows.items()
        if "source_document_id" in Base.metadata.tables[name].c for r in table_rows
    )
    return SeedReport(stats, problems, src.repairs.examples, source_types, stored)
