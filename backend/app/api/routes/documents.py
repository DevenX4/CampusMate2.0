from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import AUTH_ERRORS, NOT_FOUND, Context, DbSession, Limit, Offset, SearchText, require
from app.core.config import get_settings
from app.models.auth import User
from app.schemas.common import ErrorResponse, Page
from app.schemas.documents import (
    DocumentDetail, DocumentForm, DocumentStats, DocumentSummary, DocumentType, VersionForm, VersionOut,
)
from app.services import documents, storage
from app.services.errors import UploadRejected

router = APIRouter(prefix="/documents", tags=["documents"], responses=AUTH_ERRORS)
Reader = Annotated[User, Depends(require("documents:read"))]
Manager = Annotated[User, Depends(require("documents:manage"))]
CONFLICT = {409: {"model": ErrorResponse, "description": "Not allowed in the current state"}}
UPLOAD_ERRORS = {**CONFLICT, 413: {"model": ErrorResponse, "description": "File too large"},
                 415: {"model": ErrorResponse, "description": "Not a PDF"},
                 422: {"model": ErrorResponse, "description": "Invalid file or metadata"}}


def storage_root() -> Path:
    """Where files live. A dependency, so tests can point it at a temporary folder."""
    return get_settings().storage_dir


StorageRoot = Annotated[Path, Depends(storage_root)]


class DocumentUpload(DocumentForm):
    """Multipart form for a new document: the metadata fields plus the file itself.
    FastAPI validates every field BEFORE the endpoint runs, so no bytes are stored for an
    invalid request."""

    file: UploadFile


class VersionUpload(VersionForm):
    file: UploadFile


@contextmanager
def receiving(request: Request, file: UploadFile, root: Path) -> Iterator[tuple[storage.ReceivedFile, str, str | None]]:
    """Reject oversized requests early (by their declared length), then copy the file into
    storage/tmp while hashing it and enforcing the limit on the actual bytes. Whatever happens
    next (duplicate, not a PDF, crash), the temporary file is removed afterwards; an accepted
    upload has already been moved to its content address, so there is nothing to remove."""
    max_mb = get_settings().max_upload_mb
    declared = int(request.headers.get("content-length") or 0)
    if declared > max_mb * 1024 * 1024 + 64 * 1024:  # small allowance for the multipart envelope
        raise UploadRejected("too_large", f"File exceeds the {max_mb} MB limit")
    received = storage.receive_upload(file.file, root, max_mb * 1024 * 1024)
    try:
        yield received, documents.safe_filename(file.filename), file.content_type
    finally:
        received.discard()


@router.get("", response_model=Page[DocumentSummary])
def list_documents(
    db: DbSession, user: Reader, q: SearchText = None, document_type: DocumentType | None = None,
    source_type: Literal["official", "synthetic"] | None = None,
    # "status" would shadow fastapi.status in this module, hence the alias.
    status_filter: Annotated[Literal["active", "inactive", "archived", "deleted"] | None,
                             Query(alias="status")] = None,
    department_id: str | None = None, limit: Limit = 20, offset: Offset = 0,
):
    """Documents, most recently changed first. Deleted documents appear only with ?status=deleted."""
    return documents.list_documents(db, q=q, document_type=document_type, source_type=source_type,
                                    status=status_filter, department_id=department_id,
                                    limit=limit, offset=offset)


@router.get("/stats", response_model=DocumentStats)
def document_stats(db: DbSession, user: Reader):
    """The numbers on the admin dashboard cards."""
    return documents.stats(db)


@router.post("", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED, responses=UPLOAD_ERRORS)
def upload_document(form: Annotated[DocumentUpload, Form()], request: Request, db: DbSession,
                    admin: Manager, context: Context, root: StorageRoot):
    """Register a new document: version 1 is stored and queued for ingestion."""
    with receiving(request, form.file, root) as (received, filename, content_type):
        return documents.create_document(db, received, filename, content_type, form,
                                         storage_root=root, actor=admin, context=context)


@router.get("/{document_id}", response_model=DocumentDetail, responses=NOT_FOUND)
def get_document(document_id: str, db: DbSession, user: Reader):
    return documents.get_document(db, document_id)


@router.get("/{document_id}/versions", response_model=list[VersionOut], responses=NOT_FOUND)
def list_versions(document_id: str, db: DbSession, user: Reader):
    return documents.list_versions(db, document_id)


@router.post("/{document_id}/versions", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED,
             responses={**NOT_FOUND, **UPLOAD_ERRORS})
def upload_version(document_id: str, form: Annotated[VersionUpload, Form()], request: Request,
                   db: DbSession, admin: Manager, context: Context, root: StorageRoot):
    """Replace a document: the file becomes version N+1 (pending) and is queued for ingestion.
    The current version keeps answering until the new one is activated."""
    with receiving(request, form.file, root) as (received, filename, content_type):
        return documents.add_version(db, document_id, received, filename, content_type, form,
                                     storage_root=root, actor=admin, context=context)


@router.post("/{document_id}/versions/{version_no}/activate", response_model=DocumentDetail,
             responses={**NOT_FOUND, **CONFLICT})
def activate_version(document_id: str, version_no: int, db: DbSession, admin: Manager, context: Context):
    """Switch answers to this version (also how you roll back to an older one)."""
    return documents.activate_version(db, document_id, version_no, actor=admin, context=context)


@router.get("/{document_id}/versions/{version_no}/file", response_class=FileResponse, responses=NOT_FOUND)
def download_version(document_id: str, version_no: int, db: DbSession, admin: Manager, root: StorageRoot):
    """Download the original file (administrators only)."""
    path, version = documents.version_file(db, root, document_id, version_no)
    return FileResponse(path, media_type=version.mime_type, filename=version.original_filename)


@router.post("/{document_id}/reindex", response_model=DocumentDetail, responses={**NOT_FOUND, **CONFLICT})
def reindex_document(document_id: str, db: DbSession, admin: Manager, context: Context):
    """Queue a re-index of the active version."""
    return documents.request_reindex(db, document_id, actor=admin, context=context)


@router.post("/{document_id}/activate", response_model=DocumentDetail, responses={**NOT_FOUND, **CONFLICT})
def activate_document(document_id: str, db: DbSession, admin: Manager, context: Context):
    """Make an inactive or archived document answerable again."""
    return documents.change_status(db, document_id, "activate", actor=admin, context=context)


@router.post("/{document_id}/deactivate", response_model=DocumentDetail, responses={**NOT_FOUND, **CONFLICT})
def deactivate_document(document_id: str, db: DbSession, admin: Manager, context: Context):
    """Stop using a document for answers, without deleting anything."""
    return documents.change_status(db, document_id, "deactivate", actor=admin, context=context)


@router.post("/{document_id}/archive", response_model=DocumentDetail, responses={**NOT_FOUND, **CONFLICT})
def archive_document(document_id: str, db: DbSession, admin: Manager, context: Context):
    """Archive a document: kept for reference, not used for answers."""
    return documents.change_status(db, document_id, "archive", actor=admin, context=context)


@router.delete("/{document_id}", response_model=DocumentDetail, responses={**NOT_FOUND, **CONFLICT})
def delete_document(document_id: str, db: DbSession, admin: Manager, context: Context):
    """Soft delete: the document and its files are kept for the audit trail, but it is hidden
    from lists and never used for answers again."""
    return documents.change_status(db, document_id, "delete", actor=admin, context=context)
