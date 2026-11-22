"""Development provider: answers by copying the most relevant sentences of the context, each
with its citation. No model, no download, deterministic.

It cannot invent anything (every word comes from a source), but it cannot combine, rephrase
or reason either, and it cannot notice that the context does not really answer the question.
It is the baseline an SLM has to beat, and what CampusMate runs on until one is chosen.
"""

import math
import re
import time

from app.generation.base import ABSTAIN_MESSAGE, ContextBlock, GenerationRequest, GenerationResult
from app.retrieval.bm25 import tokenize

MAX_SENTENCES = 3
MAX_SENTENCE_CHARS = 400
# Share of the question's words (weighted by rarity) a candidate must contain to be used. Low
# enough for a two-part question, where each source answers one part.
MIN_COVERAGE = 0.35
# Words that shape a question without saying what it is about ("how MANY credits"), and
# "official", which the router turns into a filter.
QUESTION_WORDS = frozenset("many much tell please about give list explain describe know official".split())
_ROMAN = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}
# A sentence ends at . ! ? or a line break, but not after a title or an initial ("Dr. A. Patel").
_ABBREVIATIONS = ("Dr", "Mr", "Mrs", "Ms", "Prof", "No", "e.g", "i.e", "[A-Z]")
_SENTENCE_END = re.compile(r"(?<=[.!?])" + "".join(rf"(?<!\b{a}\.)" for a in _ABBREVIATIONS) + r"\s+|[\r\n]+")
SYNTHETIC_PREFIX = "(Synthetic demo data)"
SYNTHETIC_NOTE = "Synthetic demo data is not official GUNI information."


# A line break inside a sentence (a PDF line wrap): the line does not end a sentence and the next
# one continues in lower case. Found in the hallucination tests: "All dates are synthetic and are
# not / an actual Ganpat University schedule." was quoted as "an actual Ganpat University
# schedule", the opposite of what it says. "key: value" lines are not continuations.
_WRAPPED_LINE = re.compile(r"(?<![.!?:;])[ \t]*(?:\r\n|\r|\n)[ \t]*(?=[a-z])(?![a-z_]+:\s)")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(_WRAPPED_LINE.sub(" ", text)) if len(s.strip()) > 2]


def _term(token: str) -> str:
    """A light normalisation for matching only: Semester VII = semester 7, electives = elective,
    facilities = facility, examinations = exam."""
    if token in _ROMAN:
        return _ROMAN[token]
    if token in ("examination", "examinations", "exams"):
        return "exam"
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def terms(text: str) -> set[str]:
    return {_term(t) for t in tokenize(text)}


def _is_synthetic(text: str, block: ContextBlock) -> bool:
    # An official graph item can relate to synthetic entities ("taught_by: FAC-1 [synthetic]"):
    # a piece is labelled by what it says, not only by the block it came from.
    return block.source_type == "synthetic" or "[synthetic]" in text


def _cited(sentence: str, block: ContextBlock) -> str:
    cited = f"{sentence.rstrip('. ')} [{block.ref}]."
    return f"{SYNTHETIC_PREFIX} {cited}" if _is_synthetic(sentence, block) else cited


def _shorten(sentence: str) -> str:
    return sentence if len(sentence) <= MAX_SENTENCE_CHARS else sentence[:MAX_SENTENCE_CHARS].rsplit(" ", 1)[0] + " ..."


def pieces(block: ContextBlock) -> list[str]:
    """The parts of a block that can be quoted on their own."""
    if block.kind == "structured":  # one computed statement: a semester's course list must not be cut
        return [block.text]
    if block.kind == "graph":  # "Title (...). key: value; key: value. Relationships: reading: targets; ..."
        # Each clause keeps its subject: a graph item can be a neighbour of the course asked
        # about, and "practicals_in: LAB-4" alone would read as if it were about that course.
        header, *clauses = [p.removeprefix("Relationships: ") for s in sentences(block.text) for p in s.split("; ")]
        title = header.split(" (", 1)[0]
        return [header] + [f"{title}: {clause}" for clause in clauses]
    return [s for s in sentences(block.text) if not s.endswith("?")]  # a question (FAQ title) answers nothing


def extract_answer(question: str, context: list[ContextBlock]) -> str:
    candidates = [(block, text) for block in context for text in pieces(block)]
    wanted = terms(question) - QUESTION_WORDS
    token_sets = [terms(text) for _, text in candidates]
    # Rare question words (a course code) decide; words found everywhere barely count. Question
    # words found nowhere keep a high weight, so missing them lowers every coverage.
    idf = {t: math.log(1 + len(candidates) / (1 + sum(t in ts for ts in token_sets))) for t in wanted}
    # Summed in sorted order: float addition depends on order, and set order changes per process.
    total = sum(idf[t] for t in sorted(wanted))
    weights = [sum(idf[t] for t in sorted(wanted & ts)) for ts in token_sets]
    # Relevant candidates only; structured facts first (exact), then the best passage sentences.
    ranked = sorted((candidates[i][0].kind != "structured", -w, i) for i, w in enumerate(weights)
                    if total and w / total >= MIN_COVERAGE)
    chosen: list[str] = []
    covered: set[str] = set()  # question words the structured facts chosen so far answer
    synthetic = False
    for _, _, i in ranked:
        if len(chosen) == MAX_SENTENCES:
            break
        block, text = candidates[i]
        # A structured fact is a complete computed statement: after one, a passage sentence is
        # used only if it answers a part of the question the facts do not (a two-part question).
        # Otherwise the answer to "Semester VI courses" trails off into catalogue metadata lines.
        if covered and block.kind != "structured" and not (wanted & token_sets[i]) - covered:
            continue
        if not any(text.lower() in c.lower() for c in chosen):  # not said already
            chosen.append(_cited(text if block.kind == "structured" else _shorten(text), block))
            synthetic |= _is_synthetic(text, block)
            if block.kind == "structured":
                covered |= wanted & token_sets[i]
    if not chosen:
        return ABSTAIN_MESSAGE
    return " ".join(chosen + [SYNTHETIC_NOTE] if synthetic else chosen)


class ExtractiveProvider:
    name = "extractive"
    model = "extractive-v1"

    def check(self) -> str:
        return "extractive: copies cited sentences from the evidence (no model)"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        started = time.perf_counter()
        text = extract_answer(request.question, request.context)
        return GenerationResult(text, self.name, self.model, round((time.perf_counter() - started) * 1000))
