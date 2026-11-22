"""Helpers shared by several test modules."""

import io
import uuid
from pathlib import Path

from fpdf import FPDF
from pypdf import PdfWriter

from app.models.documents import Document, DocumentChunk, DocumentVersion
from app.retrieval.embeddings import HashEmbedder
from app.retrieval.indexing import ChunkIndexer
from app.retrieval.vector_index import VectorIndex
from app.schemas.users import UserCreate
from app.services import users
from app.services.audit import RequestContext

API = "/api/v1"
PASSWORD = "correct-horse-battery"


def make_pdf(pages: int = 1) -> bytes:
    """A real, tiny, blank PDF. The random title makes every file's bytes (and SHA-256) unique."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Title": uuid.uuid4().hex})
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def text_pdf(pages: list[list[str]]) -> bytes:
    """A PDF whose pages contain the given lines of text (so ingestion has something to read).
    A random line at the end keeps every generated file unique."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=10)
    for lines in pages:
        pdf.add_page()
        for line in lines:
            pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, f"ref {uuid.uuid4().hex}", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def headers_for(client, db, role: str) -> dict:
    """Create a user with this role, log in, and return an Authorization header."""
    email = f"{role}-{uuid.uuid4().hex[:6]}@campusmate-demo.example"
    users.create_user(db, UserCreate(email=email, password=PASSWORD, role=role), actor_id=None,
                      context=RequestContext())
    token = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    client.cookies.clear()  # rely on the explicit header only
    return {"Authorization": f"Bearer {token}"}


def make_indexer(folder: Path) -> ChunkIndexer:
    """A vector index in a temporary folder with the deterministic test embedder (no download)."""
    embedder = HashEmbedder()
    return ChunkIndexer(embedder, VectorIndex(folder, "test-chunks", embedder.model_name, embedder.dimension))


def add_document(db, indexer, document_id: str, chunks: list[dict], *, source_type="synthetic",
                 versions: dict[int, str] | None = None) -> None:
    """A document whose versions (status by number) each hold the given chunks, indexed."""
    document = Document(document_id=document_id, title=f"Title of {document_id}", document_type="other",
                        source_type=source_type, status="active")
    db.add(document)
    db.flush()
    for version_no, status in (versions or {1: "active"}).items():
        db.add(DocumentVersion(document_id=document_id, version_no=version_no, sha256=uuid.uuid4().hex * 2,
                               storage_key=f"k/{uuid.uuid4()}", original_filename="f.pdf",
                               mime_type="application/pdf", size_bytes=1, status=status))
        db.flush()
        rows = [DocumentChunk(chunk_id=uuid.uuid4(), document_id=document_id, version_no=version_no,
                              chunk_index=i, text=c["text"], content_sha256="x", page_start=1, page_end=1,
                              source_type=c.get("source_type", source_type),
                              metadata_={"semester_ids": c.get("semester_ids", [])})
                for i, c in enumerate(chunks)]
        db.add_all(rows)
        db.flush()
        indexer.index_chunks(document, rows)
