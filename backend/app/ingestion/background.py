"""The ingestion worker as a background thread of the API process.

Why inside the API: Chroma's embedded store may be used by one process only (Phase 18: a second
process writing to it made the API fail with "Error finding id"), and running a Chroma server
instead exposes a pre-authentication remote-code-execution flaw that has no fix
(CVE-2026-45829; found by the Phase 19 dependency audit). One process owning the store avoids
both. The jobs themselves stay durable in PostgreSQL, exactly as with the standalone worker.
"""

import logging
import threading

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.ingestion.pipeline import process_next
from app.retrieval.runtime import get_indexer

logger = logging.getLogger("campusmate.worker")


class BackgroundWorker:
    def __init__(self):
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ingestion-worker", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        """Finish the current job (it runs in one transaction), then stop."""
        self._stop.set()
        self._thread.join(timeout)

    def _run(self) -> None:
        settings = get_settings()
        indexer = get_indexer()  # loads the embedding model here, not during API start-up
        logger.info("Ingestion worker running inside the API process")
        while not self._stop.is_set():
            try:
                with SessionLocal() as db:
                    result = process_next(db, settings.storage_dir, max_chars=settings.chunk_max_chars,
                                          lease_minutes=settings.ingestion_lease_minutes, indexer=indexer)
            except Exception:  # e.g. the database is briefly unreachable: log, wait, try again
                logger.exception("Ingestion worker error")
                result = None
            if result is None:
                self._stop.wait(settings.worker_poll_seconds)
