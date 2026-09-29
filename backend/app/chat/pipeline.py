"""The chat pipeline:

    question -> router -> evidence (SQL / graph / retrieval) -> context -> generation -> grounding -> answer

Every step is deterministic except generation, and generation is checked afterwards. An answer
that fails the grounding check is never shown: the extractive answer built from the same
sources replaces it (it cannot invent anything), and if that finds nothing CampusMate abstains.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.chat.context import Context, build_context
from app.chat.grounding import GroundingReport, validate
from app.chat.tracing import is_trace_enabled, print_trace
from app.core.config import get_settings
from app.generation.base import ABSTAIN_MESSAGE, GenerationError, GenerationProvider, GenerationRequest
from app.generation.extractive import ExtractiveProvider
from app.routing.entities import EntityResolver
from app.routing.evidence import RetrievalDeps, gather
from app.routing.router import decide

logger = logging.getLogger(__name__)

# Routes CampusMate recognises but cannot serve yet: said plainly instead of searching documents.
UNSUPPORTED = {
    "personal": "CampusMate cannot see personal records such as your marks, attendance or fees yet.",
    "automation": "CampusMate cannot set reminders or carry out actions yet.",
}


@dataclass
class ChatAnswer:
    question: str
    answer: str
    answer_type: str  # answered | fallback | abstained | unsupported
    route: str
    intents: list[str]
    reasons: list[str]
    context: Context
    grounding: GroundingReport
    provider: str
    model: str
    timings_ms: dict[str, int]


class _Stopwatch:
    def __init__(self):
        self.started, self.timings = time.perf_counter(), {}

    @contextmanager
    def stage(self, name: str):
        start = time.perf_counter()
        yield
        self.timings[name] = round((time.perf_counter() - start) * 1000)

    def total(self) -> dict[str, int]:
        return {**self.timings, "total": round((time.perf_counter() - self.started) * 1000)}


def answer_question(db: Session, question: str, deps: RetrievalDeps, generator: GenerationProvider,
                    max_tokens: int = 400, temperature: float = 0.0, *, program_id: str | None = None,
                    semester_id: str | None = None) -> ChatAnswer:
    """program_id / semester_id: the programme and semester the user has selected. They apply only
    when the question names none itself ("Which courses are in this semester?")."""
    watch = _Stopwatch()
    with watch.stage("routing"):
        resolution = EntityResolver(db).resolve(question)
        defaults = []
        if program_id and not resolution.program_ids:
            resolution.program_ids, defaults = [program_id], defaults + [program_id]
        if semester_id and not resolution.semester_ids:
            resolution.semester_ids, defaults = [semester_id], defaults + [semester_id]
        decision = decide(question, resolution)
        if defaults:
            decision.reasons.append(f"from the selected context: {', '.join(defaults)}")

    generated_text_for_trace = None
    request_for_trace = None

    def finish(answer: str, answer_type: str, context: Context, report: GroundingReport) -> ChatAnswer:
        tot_timings = watch.total()
        settings = get_settings()
        if is_trace_enabled(settings):
            print_trace(
                question=question,
                route=decision.route,
                intents=decision.intents,
                reasons=decision.reasons,
                resolution=resolution,
                context=context,
                request=request_for_trace,
                generated_text=generated_text_for_trace,
                grounding=report,
                answer=answer,
                answer_type=answer_type,
                provider=generator.name,
                model=generator.model,
                timings=tot_timings,
            )
        return ChatAnswer(question, answer, answer_type, decision.route, decision.intents, decision.reasons,
                          context, report, generator.name, generator.model, tot_timings)

    if decision.route in UNSUPPORTED:
        message = UNSUPPORTED[decision.route]
        return finish(message, "unsupported", Context([], {}), GroundingReport(message, passed=True))
    if resolution.unknown_ids:
        # A question about something that does not exist ("Is LAB-IT-011 open on Sundays?") must
        # not be answered from passages about something else that merely shares its words.
        return finish(ABSTAIN_MESSAGE, "abstained", Context([], {}), GroundingReport(
            ABSTAIN_MESSAGE, passed=True, abstained=True,
            warnings=[f"not in the knowledge base: {', '.join(resolution.unknown_ids)}"]))

    with watch.stage("evidence"):
        context = build_context(gather(db, question, decision, deps), official_only=resolution.official_only)
    if not context.blocks:
        return finish(ABSTAIN_MESSAGE, "abstained", context, GroundingReport(ABSTAIN_MESSAGE, passed=True, abstained=True))

    request = GenerationRequest(question, context.blocks, max_tokens, temperature)
    request_for_trace = request
    with watch.stage("generation"):
        try:
            generated = generator.generate(request).text
            generated_text_for_trace = generated
        except GenerationError as exc:
            logger.warning("Generation failed, using the extractive answer: %s", exc)
            generated = None
    with watch.stage("grounding"):
        report = validate(generated, context.blocks) if generated is not None else None
    if report is not None and report.passed:
        return finish(report.answer, "abstained" if report.abstained else "answered", context, report)

    # The generated answer is missing or not grounded: answer from the same sources without a model.
    fallback = validate(ExtractiveProvider().generate(request).text, context.blocks)
    fallback.warnings.insert(0, "generation failed" if report is None else f"generated answer rejected: {'; '.join(report.issues)}")
    answer_type = "abstained" if fallback.abstained else "fallback"
    return finish(fallback.answer, answer_type, context, fallback)

