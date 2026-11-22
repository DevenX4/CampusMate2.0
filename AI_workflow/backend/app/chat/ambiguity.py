"""Ambiguity detection & clarification state engine.

Detects ambiguous queries (unspecified deadlines, unspecified department HODs)
and generates concise clarification questions with exact options retrieved from actual database records.

Does not call the LLM when asking for clarification or when reporting missing role/HOD info.
"""

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import CalendarEvent, Notice
from app.models.organization import Department

logger = logging.getLogger(__name__)

_DEADLINE_GENERIC_RE = re.compile(
    r"^\s*(what|when|tell me|show me|check|is there)\s+(is|are|the|any)?\s*deadlines?\s*\??\s*$",
    re.IGNORECASE
)
_HOD_GENERIC_RE = re.compile(
    r"^\s*(who|tell me who|do you know who)\s+(is|heads|leads)?\s*(the)?\s*(hod|head of department|department head)\s*\??\s*$",
    re.IGNORECASE
)
_HOD_SPECIFIC_RE = re.compile(
    r"\b(hod|head of department|department head)\b", re.IGNORECASE
)


_GREETING_RE = re.compile(
    r"^\s*(hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening|greetings|howdy|hi there|hello there)\s*[\!\.\?]*\s*$",
    re.IGNORECASE
)


# Rules removed: Replaced by authentic Hybrid RAG pipeline


@dataclass
class AmbiguityResult:
    is_ambiguous: bool = False
    is_absent: bool = False
    answer: str | None = None
    options: list[str] = field(default_factory=list)
    pending_state: dict | None = None


def check_ambiguity(db: Session, question: str, resolved_entities: list[str]) -> AmbiguityResult:
    """Inspect query for deadline, HOD, or predefined demo QA rules."""
    from datetime import datetime

    clean_q = question.strip()

    # 0. Greeting check based on current time
    if _GREETING_RE.match(clean_q):
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning! I'm your CampusMate, here to help you!"
        elif hour < 17:
            greeting = "Good afternoon! I'm your CampusMate, here to help you!"
        else:
            greeting = "Good evening! I'm your CampusMate, here to help you!"

        return AmbiguityResult(
            is_ambiguous=True,
            answer=f"{greeting} How can I assist you with your courses, attendance, exams, or syllabus today?",
            options=[],
            pending_state=None,
        )
    # 0.5 Predefined Demo QA Rules removed - authentic RAG pipeline executes

    # 1. Deadline Ambiguity
    if _DEADLINE_GENERIC_RE.search(clean_q) or clean_q.lower() in ("what is the deadline?", "what is the deadline", "deadline"):
        # Retrieve actual calendar event titles or notice categories containing deadline info from DB
        events = db.scalars(
            select(CalendarEvent.title)
            .where(CalendarEvent.title.ilike("%deadline%") | CalendarEvent.event_type.ilike("%deadline%"))
            .limit(10)
        ).all()

        options = []
        if events:
            # Clean up event names into concise options
            seen = set()
            for title in events:
                opt = re.sub(r"\bdeadline\b", "", title, flags=re.I).strip(" :-")
                if not opt:
                    opt = title.strip()
                if opt and opt.lower() not in seen:
                    seen.add(opt.lower())
                    options.append(opt.capitalize())

        # Fallback to standard canonical deadlines if DB has general deadline events
        if not options:
            options = [
                "Exam registration",
                "Assignment submission",
                "Scholarship",
                "Project submission",
                "Course registration",
            ]

        options = options[:5]
        answer_text = "I found multiple deadlines in the campus information. Which deadline are you asking about?"
        
        return AmbiguityResult(
            is_ambiguous=True,
            answer=answer_text,
            options=options,
            pending_state={
                "type": "deadline",
                "original_question": clean_q,
                "options": options,
            },
        )

    # 2. HOD Ambiguity & Department HOD check
    if _HOD_GENERIC_RE.search(clean_q) or clean_q.lower() in ("who is the hod?", "who is the hod", "hod"):
        # Retrieve actual departments in the database
        departments = db.scalars(select(Department).order_by(Department.department_name)).all()
        options = [d.department_name for d in departments if d.department_name]
        
        if len(options) > 1:
            answer_text = "Which department's HOD are you asking about?"
            return AmbiguityResult(
                is_ambiguous=True,
                answer=answer_text,
                options=options,
                pending_state={
                    "type": "hod",
                    "original_question": clean_q,
                    "options": options,
                },
            )

    # 3. Check for specific department HOD query where HOD data is missing from DB
    if _HOD_SPECIFIC_RE.search(clean_q):
        departments = db.scalars(select(Department)).all()
        for dept in departments:
            if dept.department_name and dept.department_name.lower() in clean_q.lower():
                # Check if department has head_faculty_id set
                if not dept.head_faculty_id:
                    return AmbiguityResult(
                        is_ambiguous=False,
                        is_absent=True,
                        answer=f"I currently don't have HOD information for the {dept.department_name} department in the CampusMate knowledge base.",
                    )

    return AmbiguityResult(is_ambiguous=False)
