"""Deterministic query routing: decide WHERE the evidence for a question should come from.

Ordered rules, first on the resolved entities, then on intent words. No language model is
involved, so every decision is explainable (`reasons`) and repeatable.

    automation  "remind me ..."            -> not supported yet (answered honestly)
    personal    "my marks", "my attendance" -> student records are not in CampusMate
    structured  exact facts in tables       -> SQL (course facts, a semester's courses,
                                               programme summary, elective options, grades)
    graph       an entity + a relation      -> OKF relationships ("who teaches", "which lab")
    documents   everything else             -> hybrid retrieval over document chunks

Structured and graph evidence is always SUPPORTED by document retrieval as well, so a routing
mistake costs precision, not the answer.
"""

import re
from dataclasses import dataclass, field

from app.routing.entities import Resolution

_AUTOMATION = re.compile(r"\b(remind(er)?|notify|notification|alert me|email me|send me|schedule (a|an|my))\b", re.I)
_PERSONAL = re.compile(r"\bmy (marks|grades?|results?|attendance|cgpa|sgpa|fees?|timetable|exam schedule)\b", re.I)
_GRADE = re.compile(r"\bgrade\b.*\bmarks?\b|\bmarks?\b.*\bgrade\b", re.I)
_OPTIONS = re.compile(r"\b(options?|choices?|choose|pick)\b", re.I)
_ELECTIVE_SLOT = re.compile(r"\belective[-\s]*(viii|vii|vi|iv|v|iii|ii|i)\b", re.I)
_LISTING = re.compile(r"\b(courses?|subjects?|taught|offered|electives?|curriculum)\b", re.I)
_PROGRAM_TOTALS = re.compile(r"\b(total credits?|credit requirement|how many semesters|number of semesters|"
                             r"how many credits|duration)\b", re.I)
_COURSE_FACTS = re.compile(r"\b(credits?|marks|contact hours|course code|which semester|what semester|"
                           r"examination scheme|exam scheme)\b", re.I)
_RELATION = re.compile(r"\b(teach\w*|taught|instructor|faculty member|lab|labs|laborator\w*|practicals?|"
                       r"prerequisites?|requires?|office|building|located|research areas?|coordinat\w*|head|"
                       r"in charge|manag\w*|associated|belongs?)\b", re.I)
_LOOKUP = re.compile(r"^\s*(what|which|who)\b", re.I)


@dataclass
class RouteDecision:
    route: str  # primary route: structured | graph | documents | personal | automation
    intents: list[str]
    resolution: Resolution
    reasons: list[str] = field(default_factory=list)


def decide(question: str, res: Resolution) -> RouteDecision:
    if _AUTOMATION.search(question):
        return RouteDecision("automation", ["automation"], res, ["asks for an action (reminder/notification)"])
    if _PERSONAL.search(question):
        return RouteDecision("personal", ["personal_record"], res, ["asks for the user's own records"])

    courses = res.of_type("COURSE")
    intents, reasons = [], []
    if _GRADE.search(question) and res.numbers:
        intents.append("grade_for_marks"); reasons.append("grade for a mark: grading table")
    if _OPTIONS.search(question) and (res.of_type("EGRP") or (_ELECTIVE_SLOT.search(question) and res.semester_ids)):
        intents.append("elective_slot_options"); reasons.append("options of an elective slot: offerings table")
    if courses and _COURSE_FACTS.search(question):
        intents.append("course_facts"); reasons.append(f"facts about {', '.join(courses[:3])}: offerings table")
    if res.semester_ids and _LISTING.search(question) and not courses:
        intents.append("semester_courses"); reasons.append(f"courses of {', '.join(res.semester_ids)}: offerings table")
    if res.program_ids and _PROGRAM_TOTALS.search(question) and not (courses or res.semester_ids):
        intents.append("program_summary"); reasons.append(f"totals of {', '.join(res.program_ids)}: semesters table")

    entities = [e for e in res.entity_ids if not e.startswith(("PROG-", "SEM-"))]
    if entities and _RELATION.search(question):
        intents.append("entity_relations"); reasons.append(f"relationships of {', '.join(entities[:3])}: knowledge graph")
    elif entities and not intents and _LOOKUP.search(question):
        intents.append("entity_lookup"); reasons.append(f"what {', '.join(entities[:3])} is: knowledge graph")

    intents.append("documents")
    reasons.append("supporting passages: hybrid retrieval" if len(intents) > 1 else "no structured intent: hybrid retrieval")
    primary = intents[0]
    route = ("structured" if primary in ("grade_for_marks", "elective_slot_options", "course_facts",
                                         "semester_courses", "program_summary")
             else "graph" if primary in ("entity_relations", "entity_lookup") else "documents")
    return RouteDecision(route, intents, res, reasons)
