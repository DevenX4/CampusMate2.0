"""Grounding validation: is a generated answer backed by the sources it was given?

Deterministic checks, no model. Failures (the answer is not shown):

  citations   the answer cites at least one source, and only sources that exist
  facts       every number and code (4, 150, 75%, 2CEIT602, FAC-IT-004) occurs in the sources:
              a wrong number ("3 credits" instead of 4) is the most harmful error a campus
              assistant can make
  names       every capitalised word (a person, a lab, a course) occurs in the sources

Warnings (recorded, the answer is still shown): a fact found only in a source the answer does
not cite; sentences without a citation. When a cited source is synthetic and the answer does
not say so, a notice is appended.

What it cannot catch: a wrong statement made only of words that do occur in the sources
("the lab is closed" when the source says "open"). That needs a language model as a judge;
answer evaluation measures how often it happens.
"""

import re
from dataclasses import dataclass, field

from app.generation.base import ABSTAIN_MESSAGE, ContextBlock
from app.generation.extractive import SYNTHETIC_NOTE, sentences
from app.retrieval.bm25 import STOPWORDS, tokenize

_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
# A model that refuses in its own words instead of the exact sentence.
_REFUSAL = re.compile(r"couldn.?t find|could not find|no authoritative information|do not (contain|mention)|"
                      r"(not|isn.?t) (mentioned|available|provided|stated) in the (sources|context)", re.I)
# A whole word: letters inside a code such as 2CEIT78PE7 are not a name (codes are checked as facts).
_WORD = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z'-]*(?![A-Za-z0-9])")
# Capitalised words an answer may use without a source.
_ALWAYS_KNOWN = frozenset("campusmate guni ganpat university note synthetic demo official source sources".split())


@dataclass
class GroundingReport:
    answer: str  # what may be shown: the answer, possibly with a notice, or the abstain sentence
    passed: bool
    abstained: bool = False
    cited: list[int] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def cited_refs(text: str) -> list[int]:
    return sorted({int(n) for group in _CITATION.findall(text) for n in group.split(",")})


def _is_synthetic(block: ContextBlock) -> bool:
    return block.source_type == "synthetic" or "[synthetic]" in block.text


def unknown_names(text: str, known: set[str]) -> list[str]:
    """Capitalised words that occur in no source. The first word of a sentence or clause is
    skipped: grammar capitalises it, not because it is a name."""
    unknown = set()
    for sentence in sentences(text):
        for clause in re.split(r"[:;(]\s*", sentence):
            for word in _WORD.findall(clause)[1:]:
                lower = word.lower().strip("'-")
                if (word[0].isupper() and lower not in STOPWORDS and lower not in _ALWAYS_KNOWN
                        and not set(tokenize(lower)) <= known):
                    unknown.add(word)
    return sorted(unknown)


def validate(answer: str, blocks: list[ContextBlock]) -> GroundingReport:
    text = answer.strip()
    refs = cited_refs(text)
    if not refs and (not text or _REFUSAL.search(text)):
        return GroundingReport(ABSTAIN_MESSAGE, passed=True, abstained=True)

    by_ref = {b.ref: b for b in blocks}
    # A model sees each source's header (document, page) as well as its text.
    tokens_of = {b.ref: set(tokenize(f"{b.label} {b.text}")) for b in blocks}
    known = set().union(*tokens_of.values())
    cited_known = set().union(*(tokens_of[r] for r in refs if r in tokens_of))
    body = _CITATION.sub(" ", text)
    report = GroundingReport(text, passed=False, cited=refs)

    if not refs:
        report.issues.append("the answer cites no source")
    if missing := [r for r in refs if r not in by_ref]:
        report.issues.append(f"cites sources that do not exist: {missing}")
    for token in sorted({t for t in tokenize(body) if any(c.isdigit() for c in t)}):
        if token not in known:
            report.issues.append(f"'{token}' occurs in no source")
        elif token not in cited_known:
            report.warnings.append(f"'{token}' occurs only in a source the answer does not cite")
    if names := unknown_names(body, known):
        report.issues.append(f"names that occur in no source: {', '.join(names)}")
    # The demo-data disclaimer states no fact, so it needs no citation.
    claims = [s for s in sentences(text) if s != SYNTHETIC_NOTE and _WORD.search(s)]
    if refs and (uncited := [s for s in claims if not _CITATION.search(s)]):
        report.warnings.append(f"{len(uncited)} sentence(s) without a citation")
    report.passed = not report.issues

    synthetic = [r for r in refs if r in by_ref and _is_synthetic(by_ref[r])]
    if report.passed and synthetic and not re.search(r"synthetic|demo", body, re.I):
        marks = ", ".join(f"[{r}]" for r in synthetic)
        report.answer = f"{text} Note: {marks} contains synthetic demo data, not official GUNI information."
        report.warnings.append("a synthetic source was not disclosed by the answer; a notice was added")
    return report
