"""Entity knowledge: one entity with its attributes, trust labels and typed relationships.
Used by the knowledge API and, from Phase 14, by the query router for "what is connected
to X?" questions."""

from sqlalchemy.orm import Session

from app.knowledge.graph import all_edges
from app.knowledge.okf import OKF_TYPES, build_item, find_entity, render_markdown, synthetic_entity_ids
from app.schemas.knowledge import KnowledgeItem
from app.services.errors import NotFoundError


def entity_item(db: Session, entity_id: str) -> dict:
    found = find_entity(db, entity_id)
    if found is None:
        raise NotFoundError("Entity", entity_id)
    okf_type, row = found
    return build_item(row, okf_type, all_edges(db), synthetic_entity_ids(db))


def entity_knowledge(db: Session, entity_id: str) -> KnowledgeItem:
    item = entity_item(db, entity_id)
    # Add each related entity's type and title, so a client can show "FAC-IT-002 Dr. Arjun Tensorkar".
    for targets in item["relationships"].values():
        for target in targets:
            related = find_entity(db, target["id"])
            if related is not None:
                target["type"], target["title"] = related[0], OKF_TYPES[related[0]][1](related[1])
    return KnowledgeItem.model_validate(item)


def entity_markdown(db: Session, entity_id: str) -> str:
    return render_markdown(entity_item(db, entity_id))
