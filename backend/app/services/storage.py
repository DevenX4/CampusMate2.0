"""Content-addressed storage for original documents (local disk during development).

A file is stored under its own SHA-256 fingerprint:
    storage/originals/ef/eff11f5f...d8.pdf
so identical content is stored exactly once and a stored file can never be silently
replaced by different bytes under the same name.
"""

import hashlib
import shutil
from pathlib import Path

_BLOCK = 1024 * 1024  # hash in 1 MB blocks so large PDFs are never read into memory at once


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(_BLOCK), b""):
            digest.update(block)
    return digest.hexdigest()


def original_key(sha256: str, suffix: str) -> str:
    """Storage key (relative to the storage root). Two-character sub-folders keep any one
    directory small, the same layout Git uses for its objects."""
    return f"originals/{sha256[:2]}/{sha256}{suffix.lower()}"


def store_original(storage_root: Path, source: Path, sha256: str) -> str:
    """Copy `source` into storage under its content address. No-op if already stored."""
    key = original_key(sha256, source.suffix)
    target = storage_root / key
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".part")
        shutil.copyfile(source, partial)
        partial.replace(target)  # atomic rename: a half-copied file never has the final name
    return key
