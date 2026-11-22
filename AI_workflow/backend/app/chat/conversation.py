"""Lightweight conversation history & query resolution.

Maintains bounded conversation history (last 4-6 turns) per conversation_id, handles
pronoun/reference resolution ("their research areas", "who teaches it", "how many credits does it have",
"does that apply to exams"), handles topic switching, and resolves pending clarification state.

Deterministic and entity-based resolution runs before retrieval without calling the LLM.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatQuery

logger = logging.getLogger(__name__)

# Pronominal and context continuation indicators
_THEIR_RE = re.compile(r"\b(their|his|her|they|them|he|she)\b", re.IGNORECASE)
_IT_RE = re.compile(r"\b(it|its|this|that|the course|the policy|the lab)\b", re.IGNORECASE)
_THAT_EXAM_RE = re.compile(r"\b(does|do)\s+that\s+apply\s+to\s+(exams?|examinations?)\b", re.IGNORECASE)
_SHORT_OPTION_RE = re.compile(r"^[a-z0-9\.\s\-&]{2,60}$", re.IGNORECASE)


@dataclass
class ResolvedTurn:
    original_question: str
    resolved_question: str
    entities: list[str]
    history_context: list[dict[str, str]]
    pending_state: dict | None = None
    was_clarification_reply: bool = False


def get_conversation_history(db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID | None, limit: int = 6) -> list[ChatQuery]:
    """Retrieve the recent turns for a specific conversation, newest to oldest."""
    stmt = select(ChatQuery).where(ChatQuery.conversation_id == conversation_id)
    if user_id is not None:
        stmt = stmt.where(ChatQuery.user_id == user_id)
    stmt = stmt.order_by(ChatQuery.created_at.desc()).limit(limit)
    rows = list(db.scalars(stmt))
    return list(reversed(rows))  # return in chronological order


def resolve_query_context(
    db: Session,
    question: str,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID | None,
    new_entities: list[str],
) -> ResolvedTurn:
    """Resolve follow-ups, pronouns, and pending clarification state using past conversation history."""
    history = get_conversation_history(db, conversation_id, user_id, limit=6)
    
    if not history:
        return ResolvedTurn(
            original_question=question,
            resolved_question=question,
            entities=new_entities,
            history_context=[],
            pending_state=None,
        )

    # Format bounded history context for LLM prompt (last 4-6 turns)
    history_context = []
    for q in history[-4:]:
        history_context.append({"role": "user", "content": q.question})
        history_context.append({"role": "assistant", "content": q.answer})

    last_query = history[-1]
    last_pending = last_query.pending_state or {}
    
    resolved_question = question
    entities = list(new_entities)
    pending_state = None
    was_clarification_reply = False

    # 1. Handle Pending Clarification State
    if last_query.answer_type == "clarification" and last_pending:
        pending_type = last_pending.get("type")
        options = [opt.strip().lower() for opt in last_pending.get("options", [])]
        user_input_lower = question.strip().lower()
        
        # Match option index ("1", "2") or matching text
        matched_option = None
        if user_input_lower.isdigit():
            idx = int(user_input_lower) - 1
            if 0 <= idx < len(last_pending.get("options", [])):
                matched_option = last_pending.get("options", [])[idx]
        else:
            for opt in last_pending.get("options", []):
                if opt.lower() in user_input_lower or user_input_lower in opt.lower():
                    matched_option = opt
                    break

        if not matched_option and _SHORT_OPTION_RE.match(question.strip()):
            matched_option = question.strip()

        if matched_option:
            was_clarification_reply = True
            if pending_type == "deadline":
                resolved_question = f"What is the {matched_option} deadline?"
            elif pending_type == "hod":
                resolved_question = f"Who is the HOD of {matched_option}?"
            elif pending_type == "course":
                resolved_question = f"What are the details of course {matched_option}?"
            else:
                resolved_question = f"{last_pending.get('original_question', '')} {matched_option}"
            
            logger.info("Resolved clarification reply '%s' -> '%s'", question, resolved_question)
            return ResolvedTurn(
                original_question=question,
                resolved_question=resolved_question,
                entities=entities,
                history_context=history_context,
                pending_state=None,
                was_clarification_reply=True,
            )

    # 2. Topic Switch Check
    # If the current question explicitly introduces a NEW entity or explicit domain concept
    # (e.g. Q1: "Who teaches 2CEIT602?" Q2: "What is the attendance requirement?"),
    # do NOT inherit old entities across a clear topic switch!
    has_explicit_new_entity = len(new_entities) > 0
    is_explicit_attendance_or_policy = bool(re.search(r"\b(attendance|fee|policy|grading|syllabus|registration)\b", question, re.I))
    
    if is_explicit_attendance_or_policy and not _THEIR_RE.search(question) and not _IT_RE.search(question):
        return ResolvedTurn(
            original_question=question,
            resolved_question=question,
            entities=entities,
            history_context=history_context,
            pending_state=None,
        )

    # 3. Pronominal & Direct Reference Resolution
    # Extract prior entities from history
    prior_entities = []
    for q in reversed(history):
        if q.entities:
            prior_entities.extend(q.entities)
        # break at first turn with entities to maintain most recent entity focus
        if prior_entities:
            break

    # Resolve "their" / "his" / "her" -> prior faculty / person entity
    faculty_entities = [e for e in prior_entities if e.startswith("FAC-")]
    course_entities = [e for e in prior_entities if e.startswith("COURSE-")]
    
    if _THEIR_RE.search(question) and faculty_entities:
        if not any(e.startswith("FAC-") for e in entities):
            entities.extend(faculty_entities)
            # If question is e.g. "What are their research areas?" or "Where do they work?"
            resolved_question = f"{question} (Faculty: {faculty_entities[0]})"
            logger.info("Resolved faculty pronoun 'their' -> %s", faculty_entities[0])

    elif _IT_RE.search(question) and course_entities:
        if not any(e.startswith("COURSE-") for e in entities):
            entities.extend(course_entities)
            # Resolve "it" -> course entity
            resolved_question = f"{question} (Course: {course_entities[0]})"
            logger.info("Resolved course pronoun 'it' -> %s", course_entities[0])

    # Special case: "Does that apply to exams?" after discussing attendance
    if _THAT_EXAM_RE.search(question):
        for q in reversed(history):
            if re.search(r"\battendance\b", q.question, re.I):
                resolved_question = "Does the attendance requirement apply to end-semester examinations eligibility?"
                break

    return ResolvedTurn(
        original_question=question,
        resolved_question=resolved_question,
        entities=entities,
        history_context=history_context,
        pending_state=pending_state,
        was_clarification_reply=was_clarification_reply,
    )
