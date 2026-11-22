from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.api.deps import NOT_FOUND, DbSession, require
from app.schemas.knowledge import KnowledgeItem
from app.services import knowledge

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(require("catalog:read"))])


@router.get("/entities/{entity_id}", response_model=KnowledgeItem, responses=NOT_FOUND)
def get_entity(entity_id: str, db: DbSession):
    """Any entity (course, faculty, policy, lab, notice, ...) with its attributes, per-attribute
    trust labels and typed relationships in both directions, generated from PostgreSQL."""
    return knowledge.entity_knowledge(db, entity_id)


@router.get("/entities/{entity_id}/okf", response_class=PlainTextResponse, responses=NOT_FOUND)
def get_entity_okf(entity_id: str, db: DbSession):
    """The same entity as an OKF file (YAML front-matter + labelled Markdown)."""
    return PlainTextResponse(knowledge.entity_markdown(db, entity_id), media_type="text/markdown; charset=utf-8")
