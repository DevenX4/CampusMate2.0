"""Command line: load the CampusMate dataset into PostgreSQL.

    python -m app.seed             seed and commit (safe to run repeatedly)
    python -m app.seed --dry-run   do everything, print the report, then roll back
"""

import argparse
import sys

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.seed.run import seed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.seed", description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="validate and report, then roll back")
    args = parser.parse_args(argv)

    settings = get_settings()
    setup_logging(settings.log_level)
    print(f"Seeding {settings.db_name} on {settings.db_host}:{settings.db_port} from {settings.data_dir}")

    with SessionLocal() as session:  # one transaction for the whole seed
        report = seed(session, settings.data_dir, None if args.dry_run else settings.storage_dir)
        print(report.render())
        if report.problems:
            session.rollback()
            print("ROLLED BACK: the database is unchanged.")
            return 1
        if args.dry_run:
            session.rollback()
            print("DRY RUN: rolled back, nothing was written.")
            return 0
        session.commit()
        print("COMMITTED.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
