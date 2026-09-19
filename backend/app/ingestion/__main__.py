"""Ingestion command line.

    python -m app.ingestion worker           process jobs forever (run in its own terminal)
    python -m app.ingestion worker --once    process every waiting job, then exit
    python -m app.ingestion queue-missing    queue jobs for active versions that have no chunks
                                             (e.g. the seeded dataset documents)
"""

import argparse
import logging
import sys
import time

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.ingestion.pipeline import process_next
from app.services.ingestion_jobs import queue_missing

logger = logging.getLogger("campusmate.worker")


def run_worker(once: bool) -> int:
    settings = get_settings()
    processed = 0
    logger.info("Worker started (once=%s)", once)
    while True:
        with SessionLocal() as db:
            result = process_next(db, settings.storage_dir, max_chars=settings.chunk_max_chars,
                                  lease_minutes=settings.ingestion_lease_minutes)
        if result is not None:
            processed += 1
            print(f"{result.status:9} job {result.job_id} "
                  f"{f'chunks={result.chunk_count}' if result.chunk_count is not None else result.error}")
            continue
        if once:
            return processed
        time.sleep(settings.worker_poll_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.ingestion")
    commands = parser.add_subparsers(dest="command", required=True)
    worker = commands.add_parser("worker", help="process ingestion jobs")
    worker.add_argument("--once", action="store_true", help="exit when no job is waiting")
    commands.add_parser("queue-missing", help="queue jobs for active versions without chunks")
    args = parser.parse_args(argv)
    setup_logging(get_settings().log_level)

    if args.command == "queue-missing":
        with SessionLocal() as db:
            print(f"Queued {queue_missing(db)} job(s).")
    else:
        try:
            print(f"Processed {run_worker(args.once)} job(s).")
        except KeyboardInterrupt:
            print("Worker stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
