"""Helpers shared by several test modules."""

import io
import uuid

from fpdf import FPDF
from pypdf import PdfWriter

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
