"""
Direct ingestion script — no PostgreSQL required.
Reads PDFs from AI_workflow/DataSource/, chunks them, embeds into Chroma.

Run from AI_workflow/backend/:
    python ingest_datasource.py

Idempotent: re-running clears existing vectors for a file before re-adding.
"""

import sys
import uuid
import hashlib
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent          # AI_workflow/backend/
BACKEND_DIR = SCRIPT_DIR                               # same
REPO_ROOT   = SCRIPT_DIR.parent.parent                 # project root
DATASOURCE  = REPO_ROOT / "AI_workflow" / "DataSource"
CHROMA_DIR  = REPO_ROOT / "AI_workflow" / "storage" / "chroma"

sys.path.insert(0, str(BACKEND_DIR))

from app.ingestion.extract   import extract_pages
from app.ingestion.clean     import clean_pages
from app.ingestion.chunking  import chunk_pages
from app.retrieval.runtime   import get_embedder, get_vector_index
from app.retrieval.vector_index import VectorItem

CHROMA_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_MAX_CHARS = 1200   # matches AI_workflow settings default


def doc_id(path: Path) -> str:
    """Stable ID from filename — safe to rerun without duplicating vectors."""
    return hashlib.md5(path.name.encode()).hexdigest()[:16]


def ingest_pdf(path: Path, embedder, index) -> int:
    print(f"\n→ Ingesting: {path.name}")
    d_id = doc_id(path)
    source_type = "official" if "official" in str(path) else "synthetic"

    # Extract text
    pages = extract_pages(path)
    if not pages:
        print(f"  ⚠  No pages extracted, skipping.")
        return 0

    # Clean + chunk
    cleaned = clean_pages(pages)
    chunks  = chunk_pages(cleaned.pages, CHUNK_MAX_CHARS)
    if not chunks:
        print(f"  ⚠  No chunks produced, skipping.")
        return 0

    print(f"  Pages: {len(pages)}  Chunks: {len(chunks)}")

    # Remove existing vectors for this doc before re-indexing
    try:
        index.delete_version(f"{d_id}:v1", set())
    except Exception:
        pass  # nothing to delete on first run

    # Embed + upsert into Chroma
    texts   = [c.text for c in chunks]
    vectors = embedder.embed_documents(texts)

    items = [
        VectorItem(
            chunk_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{d_id}:{i}")),
            vector=vec,
            text=text,
            metadata={
                "version_key":    f"{d_id}:v1",
                "document_id":    d_id,
                "version_no":     1,
                "source_type":    source_type,
                "document_type":  "pdf",
                "title":          path.stem.replace("_", " "),
            }
        )
        for i, (vec, text) in enumerate(zip(vectors, texts))
    ]

    index.upsert(items)
    print(f"  ✓  {len(items)} vectors added (doc_id={d_id})")
    return len(items)


def main():
    pdfs = sorted(DATASOURCE.rglob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {DATASOURCE}")
        sys.exit(1)

    print(f"Found {len(pdfs)} PDFs in {DATASOURCE}")
    print("Loading embedding model (first run downloads ~130 MB)...")

    embedder = get_embedder()
    index    = get_vector_index()

    total = 0
    for pdf in pdfs:
        try:
            total += ingest_pdf(pdf, embedder, index)
        except Exception as e:
            print(f"  ✗  Error on {pdf.name}: {e}")

    print(f"\n✅ Done — {total} total vectors in Chroma.")


if __name__ == "__main__":
    main()
