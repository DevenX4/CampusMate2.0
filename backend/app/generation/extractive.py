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
# Words that shape a question without saying what it is about ("how MANY credits").
QUESTION_WORDS = frozenset("many much tell please about give list explain describe know".split())
# A sentence ends at . ! ? or a line break, but not after a title or an initial ("Dr. A. Patel").
_ABBREVIATIONS = ("Dr", "Mr", "Mrs", "Ms", "Prof", "No", "e.g", "i.e", "[A-Z]")
_SENTENCE_END = re.compile(r"(?<=[.!?])" + "".join(rf"(?<!\b{a}\.)" for a in _ABBREVIATIONS) + r"\s+|[\r\n]+")
SYNTHETIC_PREFIX = "(Synthetic demo data, not official GUNI information)"


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if len(s.strip()) > 2]


def _cited(sentence: str, block: ContextBlock) -> str:
    cited = f"{sentence.rstrip('. ')} [{block.ref}]."
    # An official graph item can relate to synthetic entities ("taught_by: FAC-1 [synthetic]"):
    # the piece is labelled by what it says, not only by the block it came from.
    synthetic = block.source_type == "synthetic" or "[synthetic]" in sentence
    return f"{SYNTHETIC_PREFIX} {cited}" if synthetic else cited


def _shorten(sentence: str) -> str:
    return sentence if len(sentence) <= MAX_SENTENCE_CHARS else sentence[:MAX_SENTENCE_CHARS].rsplit(" ", 1)[0] + " ..."


def pieces(block: ContextBlock) -> list[str]:
    """The parts of a block that can be quoted on their own."""
    if block.kind == "structured":  # one computed statement: a semester's course list must not be cut
        return [block.text]
    if block.kind == "graph":  # "Title (...). key: value; key: value. Relationships: reading: targets; ..."
        return [p.removeprefix("Relationships: ") for s in sentences(block.text) for p in s.split("; ")]
    return [s for s in sentences(block.text) if not s.endswith("?")]  # a question (FAQ title) answers nothing


def extract_answer(question: str, context: list[ContextBlock]) -> str:
    candidates = [(block, text) for block in context for text in pieces(block)]
    wanted = set(tokenize(question)) - QUESTION_WORDS
    token_sets = [set(tokenize(text)) for _, text in candidates]
    # Rare question words (a course code) decide; words found everywhere barely count. Question
    # words found nowhere keep a high weight, so missing them lowers every coverage.
    idf = {t: math.log(1 + len(candidates) / (1 + sum(t in ts for ts in token_sets))) for t in wanted}
    total = sum(idf.values())
    weights = [sum(idf[t] for t in wanted & ts) for ts in token_sets]
    # Relevant candidates only; structured facts first (exact), then the best passage sentences.
    ranked = sorted((candidates[i][0].kind != "structured", -w, i) for i, w in enumerate(weights)
                    if total and w / total >= MIN_COVERAGE)
    chosen: list[str] = []
    for _, _, i in ranked:
        if len(chosen) == MAX_SENTENCES:
            break
        block, text = candidates[i]
        if not any(text.lower() in c.lower() for c in chosen):  # not said already
            chosen.append(_cited(text if block.kind == "structured" else _shorten(text), block))
    return " ".join(chosen) if chosen else ABSTAIN_MESSAGE


class ExtractiveProvider:
    name = "extractive"
    model = "extractive-v1"

    def check(self) -> str:
        return "extractive: copies cited sentences from the evidence (no model)"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        started = time.perf_counter()
        text = extract_answer(request.question, request.context)
        return GenerationResult(text, self.name, self.model, round((time.perf_counter() - started) * 1000))
