"""Entity resolution: which known entities does a question mention?

Recognised, from most to least exact:
- IDs as written (COURSE-2CEIT602, FAC-IT-004, POLICY-001) and printed course codes (2CEIT602);
- policy numbers (CM-SYN-POL-004);
- names of courses, faculty, labs, facilities, policies, research areas (whole words,
  case-insensitive, longest match first), faculty surnames, and acronyms of course and lab
  names ("AI") when written in capitals and pointing to exactly one entity ("IT" is both
  the department and the acronym of several course names, so it is never used);
- programmes (B.Tech / M.Tech) and semesters ("Semester VI", "sem 6", "6th semester");
- whether the user asks for official sources only.
"""

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.enrich import find_entity_ids
from app.models.campus import Facility, Laboratory
from app.models.content import Policy
from app.models.curriculum import Course, Program
from app.models.organization import Department, ResearchArea
from app.models.people import Faculty
from app.services.entities import known_entity_ids

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8}
_SEMESTER = re.compile(r"\bsem(?:ester)?\s*(\d{1,2}|viii|vii|vi|iv|v|iii|ii|i)\b|\b(\d)(?:st|nd|rd|th)\s+sem(?:ester)?\b",
                       re.IGNORECASE)
_BTECH = re.compile(r"\bb\.?\s?tech\b", re.IGNORECASE)
_MTECH = re.compile(r"\bm\.?\s?tech\b", re.IGNORECASE)
_OFFICIAL = re.compile(r"\bofficial(ly)?\b|according to the syllabus", re.IGNORECASE)
_NOISE_WORDS = {"lab", "laboratory", "and", "of", "the", "for", "in", "to", "&"}


@dataclass
class Resolution:
    entity_ids: list[str] = field(default_factory=list)  # in order of appearance
    program_ids: list[str] = field(default_factory=list)
    semester_ids: list[str] = field(default_factory=list)
    official_only: bool = False
    numbers: list[float] = field(default_factory=list)

    def of_type(self, prefix: str) -> list[str]:
        return [e for e in self.entity_ids if e.startswith(prefix + "-")]


def _acronym(name: str) -> str | None:
    words = [w for w in re.findall(r"[A-Za-z]+", name) if w.lower() not in _NOISE_WORDS]
    return "".join(w[0] for w in words).upper() if len(words) >= 2 else None


class EntityResolver:
    """Built from the database; cheap enough (a few hundred names) to build per request."""

    def __init__(self, db: Session):
        self.known_ids = known_entity_ids(db)
        names: dict[str, set[str]] = {}
        acronyms: dict[str, set[str]] = {}

        def add(name: str | None, entity_id: str) -> None:
            if name and len(name) >= 4:
                names.setdefault(name.lower(), set()).add(entity_id)

        for c in db.scalars(select(Course)):
            add(c.course_name, c.course_id)
            if (a := _acronym(c.course_name)) and len(a) >= 2:
                acronyms.setdefault(a, set()).add(c.course_id)
        for f in db.scalars(select(Faculty)):
            add(f.name, f.faculty_id)
            add(f.name.split()[-1], f.faculty_id)  # surname
        for lab in db.scalars(select(Laboratory)):
            add(lab.lab_name, lab.lab_id)
            if (a := _acronym(lab.lab_name)) and len(a) >= 2:
                acronyms.setdefault(a, set()).add(lab.lab_id)
        for f in db.scalars(select(Facility)):
            add(f.facility_name, f.facility_id)
        for p in db.scalars(select(Policy)):
            add(re.sub(r"\s*\(demo\)", "", p.title, flags=re.IGNORECASE), p.policy_id)
            add(p.policy_number, p.policy_id)
        for r in db.scalars(select(ResearchArea)):
            add(r.name, r.research_area_id)
        self.programs = {p.program_id: p.short_name for p in db.scalars(select(Program))}
        department_codes = {d.short_name.upper() for d in db.scalars(select(Department)) if d.short_name}
        # An acronym is only trusted if it names exactly one entity and is not a department code.
        acronyms = {a: ids for a, ids in acronyms.items() if len(ids) == 1 and a not in department_codes}
        # Longest names first, so "deep learning" is not also matched inside a longer name.
        self.names = sorted(names.items(), key=lambda item: len(item[0]), reverse=True)
        self.acronyms = acronyms

    def resolve(self, question: str) -> Resolution:
        found: list[tuple[int, str]] = []  # (position, entity id)
        for entity_id in find_entity_ids(question, self.known_ids):
            code = entity_id.removeprefix("COURSE-")
            position = question.upper().find(code if code != entity_id else entity_id)
            found.append((max(position, 0), entity_id))

        lowered = question.lower()
        taken: list[tuple[int, int]] = []
        for name, ids in self.names:
            for match in re.finditer(r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])", lowered):
                span = match.span()
                if any(a < span[1] and span[0] < b for a, b in taken):
                    continue  # inside a longer name already matched
                taken.append(span)
                found += [(span[0], entity_id) for entity_id in sorted(ids)]
        for acronym, ids in self.acronyms.items():  # only when written in capitals: "AI", "NLP"
            for match in re.finditer(r"\b" + re.escape(acronym) + r"\b", question):
                found += [(match.start(), entity_id) for entity_id in sorted(ids)]

        ordered: list[str] = []
        for _, entity_id in sorted(found):
            if entity_id not in ordered:
                ordered.append(entity_id)

        programs = [pid for pid, pattern in (("PROG-BTECH-IT-001", _BTECH), ("PROG-MTECH-IT-001", _MTECH))
                    if pid in self.programs and pattern.search(question)]
        return Resolution(ordered, programs, self._semesters(question, programs),
                          bool(_OFFICIAL.search(question)),
                          [float(n) for n in re.findall(r"\b\d{1,3}(?:\.\d+)?\b", question)])

    @staticmethod
    def _semesters(question: str, programs: list[str]) -> list[str]:
        semesters = []
        for match in _SEMESTER.finditer(question):
            raw = (match.group(1) or match.group(2)).lower()
            number = ROMAN.get(raw) or int(raw)
            # M.Tech IT has 4 semesters: a higher number can only be B.Tech.
            candidates = programs or (["PROG-BTECH-IT-001"] if number > 4 else
                                      ["PROG-BTECH-IT-001", "PROG-MTECH-IT-001"])
            for program in candidates:
                kind = "BTECH" if "BTECH" in program else "MTECH"
                semesters.append(f"SEM-{kind}-IT-{number:02d}")
        return list(dict.fromkeys(semesters))
