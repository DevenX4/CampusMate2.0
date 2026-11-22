"""The chat pipeline:

    question -> conversation resolution -> ambiguity check -> router -> evidence -> context -> generation -> grounding -> answer

Every step is deterministic except generation, and generation is checked afterwards. An answer
that fails the grounding check is never shown: the extractive answer built from the same
sources replaces it, and if that finds nothing CampusMate abstains.
"""

import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.chat.ambiguity import check_ambiguity
from app.chat.context import Context, build_context
from app.chat.conversation import resolve_query_context
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
    answer_type: str  # answered | fallback | abstained | unsupported | clarification
    route: str
    intents: list[str]
    reasons: list[str]
    context: Context
    grounding: GroundingReport
    provider: str
    model: str
    timings_ms: dict[str, int]
    conversation_id: uuid.UUID = field(default_factory=uuid.uuid4)
    clarification_required: bool = False
    options: list[str] = field(default_factory=list)
    pending_state: dict | None = None
    entities: list[str] = field(default_factory=list)


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


def answer_question(
    db: Session,
    question: str,
    deps: RetrievalDeps,
    generator: GenerationProvider,
    max_tokens: int = 400,
    temperature: float = 0.0,
    *,
    program_id: str | None = None,
    semester_id: str | None = None,
    conversation_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> ChatAnswer:
    """program_id / semester_id: selected context filters.
    conversation_id / user_id: multi-turn chat history context & security isolation.
    """
    watch = _Stopwatch()
    conv_id = conversation_id or uuid.uuid4()

    # Stage 1: Conversation Resolution (Follow-up understanding, pronouns, pending state)
    with watch.stage("conversation_resolution"):
        entity_resolver = EntityResolver(db)
        initial_resolution = entity_resolver.resolve(question)
        resolved_turn = resolve_query_context(
            db, question, conv_id, user_id, initial_resolution.entity_ids
        )
        query_to_route = resolved_turn.resolved_question

    # Stage 2: Ambiguity Detection (Fast deterministic check)
    ambiguity = check_ambiguity(db, query_to_route, resolved_turn.entities)

    def finish(
        answer: str,
        answer_type: str,
        context: Context,
        report: GroundingReport,
        route: str = "documents",
        intents: list[str] | None = None,
        reasons: list[str] | None = None,
        clarification_required: bool = False,
        options: list[str] | None = None,
        pending_state: dict | None = None,
        resolution: any = None,
    ) -> ChatAnswer:
        tot_timings = watch.total()
        settings = get_settings()
        final_intents = intents if intents is not None else ["documents"]
        final_reasons = reasons if reasons is not None else []
        final_options = options if options is not None else []

        if is_trace_enabled(settings):
            print_trace(
                question=question,
                route=route,
                intents=final_intents,
                reasons=final_reasons,
                resolution=resolution or initial_resolution,
                context=context,
                request=None,
                generated_text=None,
                grounding=report,
                answer=answer,
                answer_type=answer_type,
                provider=generator.name,
                model=generator.model,
                timings=tot_timings,
                conversation_id=conv_id,
                resolved_question=query_to_route,
                ambiguity_info={
                    "is_ambiguous": clarification_required,
                    "options": final_options,
                } if clarification_required else None,
            )

        return ChatAnswer(
            question=question,
            answer=answer,
            answer_type=answer_type,
            route=route,
            intents=final_intents,
            reasons=final_reasons,
            context=context,
            grounding=report,
            provider=generator.name,
            model=generator.model,
            timings_ms=tot_timings,
            conversation_id=conv_id,
            clarification_required=clarification_required,
            options=final_options,
            pending_state=pending_state,
            entities=resolved_turn.entities,
        )

    # Handle Clarification / Greeting Trigger
    if ambiguity.is_ambiguous:
        is_greeting = ambiguity.pending_state is None and not ambiguity.options
        return finish(
            answer=ambiguity.answer,
            answer_type="answered" if is_greeting else "clarification",
            context=Context([], {}),
            report=GroundingReport(ambiguity.answer, passed=True),
            route="documents",
            intents=["greeting"] if is_greeting else ["ambiguity_clarification"],
            reasons=["Greeting response based on time of day"] if is_greeting else ["Ambiguous question: requesting clarification from user"],
            clarification_required=not is_greeting,
            options=ambiguity.options,
            pending_state=ambiguity.pending_state,
        )

    # Handle Missing Information / Role Abstention
    if ambiguity.is_absent:
        return finish(
            answer=ambiguity.answer,
            answer_type="abstained",
            context=Context([], {}),
            report=GroundingReport(ambiguity.answer, passed=True, abstained=True),
            route="documents",
            intents=["missing_information"],
            reasons=["Specific entity/role information not available in knowledge base"],
        )

    # Stage 3: Query Routing
    with watch.stage("routing"):
        resolution = entity_resolver.resolve(query_to_route)
        if resolved_turn.entities:
            resolution.entity_ids = list(dict.fromkeys(resolved_turn.entities + resolution.entity_ids))

        defaults = []
        if program_id and not resolution.program_ids:
            resolution.program_ids, defaults = [program_id], defaults + [program_id]
        if semester_id and not resolution.semester_ids:
            resolution.semester_ids, defaults = [semester_id], defaults + [semester_id]
        decision = decide(query_to_route, resolution)
        if defaults:
            decision.reasons.append(f"from the selected context: {', '.join(defaults)}")

    if decision.route in UNSUPPORTED:
        message = UNSUPPORTED[decision.route]
        return finish(
            message,
            "unsupported",
            Context([], {}),
            GroundingReport(message, passed=True),
            route=decision.route,
            intents=decision.intents,
            reasons=decision.reasons,
            resolution=resolution,
        )

    if resolution.unknown_ids:
        return finish(
            ABSTAIN_MESSAGE,
            "abstained",
            Context([], {}),
            GroundingReport(
                ABSTAIN_MESSAGE,
                passed=True,
                abstained=True,
                warnings=[f"not in the knowledge base: {', '.join(resolution.unknown_ids)}"],
            ),
            route=decision.route,
            intents=decision.intents,
            reasons=decision.reasons,
            resolution=resolution,
        )

    # Stage 4: Evidence Gathering & Context Building
    with watch.stage("evidence"):
        context = build_context(gather(db, query_to_route, decision, deps), official_only=resolution.official_only)

    if not context.blocks:
        return finish(
            ABSTAIN_MESSAGE,
            "abstained",
            context,
            GroundingReport(ABSTAIN_MESSAGE, passed=True, abstained=True),
            route=decision.route,
            intents=decision.intents,
            reasons=decision.reasons,
            resolution=resolution,
        )

    # Stage 5: Response Generation (LLM or Extractive)
    request = GenerationRequest(
        question=query_to_route,
        context=context.blocks,
        max_tokens=max_tokens,
        temperature=temperature,
        history=resolved_turn.history_context,
    )
    request_for_trace = request
    generated_text_for_trace = None

    with watch.stage("generation"):
        try:
            generated = generator.generate(request).text
            generated_text_for_trace = generated
        except GenerationError as exc:
            logger.warning("Generation failed, using the extractive answer: %s", exc)
            generated = None

    # Stage 6: Grounding Validation
    with watch.stage("grounding"):
        report = validate(generated, context.blocks) if generated is not None else None

    if report is not None and report.passed:
        return finish(
            report.answer,
            "abstained" if report.abstained else "answered",
            context,
            report,
            route=decision.route,
            intents=decision.intents,
            reasons=decision.reasons,
            resolution=resolution,
        )

    # Fallback to Extractive Provider
    fallback = validate(ExtractiveProvider().generate(request).text, context.blocks)
    fallback.warnings.insert(
        0,
        "generation failed"
        if report is None
        else f"generated answer rejected: {'; '.join(report.issues)}",
    )
    answer_type = "abstained" if fallback.abstained else "fallback"

    return finish(
        fallback.answer,
        answer_type,
        context,
        fallback,
        route=decision.route,
        intents=decision.intents,
        reasons=decision.reasons,
        resolution=resolution,
    )
