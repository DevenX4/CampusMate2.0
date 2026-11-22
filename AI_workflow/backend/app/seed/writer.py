"""Step 3 of seeding: write rows so that running the seed again changes nothing (idempotent).

Three write modes:
  upsert       insert new rows; update existing rows ONLY where a value actually differs
  insert_only  insert new rows; never touch existing ones (their lifecycle belongs to admins)
  sync         upsert, then delete rows (within a scope) that are no longer in the dataset
"""

from dataclasses import dataclass

from sqlalchemy import ColumnElement, Table, delete, func, not_, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session


@dataclass
class TableStats:
    table: str
    rows: int  # rows the dataset wants in the table
    inserted: int = 0
    updated: int = 0
    deleted: int = 0

    @property
    def unchanged(self) -> int:
        return self.rows - self.inserted - self.updated


def _count(session: Session, table: Table) -> int:
    return session.scalar(select(func.count()).select_from(table))


def write(session: Session, table: Table, rows: list[dict], mode: str,
          scope: ColumnElement[bool] | None = None) -> TableStats:
    stats = TableStats(table.name, len(rows))
    if not rows:
        return stats
    pk = list(table.primary_key.columns)
    data_cols = [c for c in rows[0] if c not in {col.name for col in pk}]

    stmt = insert(table).values(rows)
    if mode == "insert_only" or not data_cols:
        stmt = stmt.on_conflict_do_nothing(index_elements=pk)
    else:
        changes = {c: stmt.excluded[c] for c in data_cols}
        if "updated_at" in table.c:
            changes["updated_at"] = func.now()
        stmt = stmt.on_conflict_do_update(
            index_elements=pk,
            set_=changes,
            # Only rewrite a row if some value is really different (IS DISTINCT FROM
            # treats NULL = NULL as "not different", unlike the plain = operator).
            where=or_(*(table.c[c].is_distinct_from(stmt.excluded[c]) for c in data_cols)),
        )

    before = _count(session, table)
    touched = len(session.execute(stmt.returning(*pk)).all())  # inserted + actually updated
    stats.inserted = _count(session, table) - before
    stats.updated = touched - stats.inserted

    if mode == "sync":
        wanted = [tuple(r[c.name] for c in pk) for r in rows]
        stale = not_(tuple_(*pk).in_(wanted))
        stats.deleted = session.execute(
            delete(table).where(stale if scope is None else stale & scope)
        ).rowcount
    return stats
