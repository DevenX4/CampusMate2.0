"""Checks that a file really is a usable PDF, whatever its name or declared type says."""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.errors import UploadRejected

PDF_MAGIC = b"%PDF-"  # every PDF file starts with these bytes


def inspect_pdf(path: Path) -> int:
    """Return the page count, or raise UploadRejected if the file is not a readable PDF."""
    with path.open("rb") as f:
        if f.read(len(PDF_MAGIC)) != PDF_MAGIC:
            raise UploadRejected("unsupported_type", "The file content is not a PDF")
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise UploadRejected("invalid", "Password-protected PDFs cannot be indexed")
        pages = len(reader.pages)
    except (PdfReadError, ValueError, OSError) as exc:
        raise UploadRejected("invalid", f"The PDF could not be read: {exc}") from exc
    if pages == 0:
        raise UploadRejected("invalid", "The PDF has no pages")
    return pages
