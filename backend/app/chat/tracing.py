"""Developer-friendly terminal pipeline tracing for CampusMate.

Provides readable execution traces for /chat/query requests when PIPELINE_TRACE=true
or when logger 'campusmate.pipeline' is enabled.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.chat.context import Context
    from app.chat.grounding import GroundingReport
    from app.generation.base import GenerationRequest

logger = logging.getLogger("campusmate.pipeline")


def is_trace_enabled(settings=None) -> bool:
    if settings is not None and getattr(settings, "pipeline_trace", False):
        return True
    return logger.isEnabledFor(logging.INFO) or logger.isEnabledFor(logging.DEBUG)


def print_trace(
    question: str,
    route: str,
    intents: list[str],
    reasons: list[str],
    resolution: Any,
    context: "Context",
    request: "GenerationRequest | None",
    generated_text: str | None,
    grounding: "GroundingReport | None",
    answer: str,
    answer_type: str,
    provider: str,
    model: str,
    timings: dict[str, int],
    retrieval_details: dict[str, Any] | None = None,
):
    """Print structured developer trace to stdout/logger without leaking API keys or secrets."""
    lines = []
    lines.append("════════════════════════════════════════════════════")
    lines.append(" CAMPUSMATE PIPELINE TRACE")
    lines.append("════════════════════════════════════════════════════")
    lines.append("")
    lines.append("[1] USER QUERY")
    lines.append(f"    {question}")
    lines.append("")
    lines.append("[2] QUERY ROUTING")
    lines.append(f"    route        : {route}")
    lines.append(f"    intents      : {', '.join(intents) if intents else 'none'}")
    if resolution:
        if resolution.entity_ids:
            lines.append(f"    entities     : {', '.join(resolution.entity_ids)}")
        if resolution.numbers:
            lines.append(f"    numbers      : {resolution.numbers}")
    for r in reasons:
        lines.append(f"    reason       : {r}")
    lines.append("")

    if retrieval_details:
        lines.append("[3] HYBRID RETRIEVAL & FUSION DETAILS")
        if "vector_hits" in retrieval_details:
            lines.append(f"    [3A] Dense Vector Candidates ({len(retrieval_details['vector_hits'])}):")
            for h in retrieval_details["vector_hits"][:5]:
                lines.append(f"         rank {h['rank']}: score={h['score']:.4f} | {h['label']} (p.{h['page']})")
        if "bm25_hits" in retrieval_details:
            lines.append(f"    [3B] BM25 Lexical Candidates ({len(retrieval_details['bm25_hits'])}):")
            for h in retrieval_details["bm25_hits"][:5]:
                lines.append(f"         rank {h['rank']}: score={h['score']:.4f} | {h['label']} (p.{h['page']})")
        if "rrf_hits" in retrieval_details:
            lines.append(f"    [3C] RRF Fused Top Results ({len(retrieval_details['rrf_hits'])}):")
            for h in retrieval_details["rrf_hits"][:5]:
                lines.append(f"         rank {h['rank']}: rrf_score={h['score']:.4f} | {h['label']}")
        lines.append("")

    lines.append("[4] CONTEXT BUILDER")
    lines.append(f"    blocks count : {len(context.blocks)}")
    total_chars = sum(len(b.text) for b in context.blocks)
    lines.append(f"    total chars  : {total_chars} / 6000")
    for block in context.blocks:
        preview = block.text.replace("\n", " ")
        if len(preview) > 90:
            preview = preview[:90] + "..."
        lines.append(f"    [{block.ref}] [{block.source_type.upper()}] {block.label}")
        lines.append(f"        preview  : \"{preview}\"")
    lines.append("")

    lines.append("[5] GENERATION ENGINE")
    lines.append(f"    provider     : {provider}")
    lines.append(f"    model        : {model}")
    if generated_text is not None:
        gen_preview = generated_text.replace("\n", " ")
        if len(gen_preview) > 100:
            gen_preview = gen_preview[:100] + "..."
        lines.append(f"    generated    : \"{gen_preview}\"")
    else:
        lines.append("    generated    : None (using fallback)")
    lines.append("")

    lines.append("[6] GROUNDING VALIDATION")
    if grounding:
        lines.append(f"    passed       : {grounding.passed}")
        lines.append(f"    abstained    : {grounding.abstained}")
        lines.append(f"    citations    : {grounding.cited if grounding.cited else 'none'}")
        if grounding.issues:
            lines.append(f"    issues       : {'; '.join(grounding.issues)}")
        else:
            lines.append("    issues       : none")
        if grounding.warnings:
            lines.append(f"    warnings     : {'; '.join(grounding.warnings)}")
        else:
            lines.append("    warnings     : none")
    else:
        lines.append("    status       : skipped")
    lines.append("")

    lines.append("[7] FINAL ANSWER & TYPE")
    lines.append(f"    answer_type  : {answer_type}")
    ans_preview = answer.replace("\n", " ")
    if len(ans_preview) > 120:
        ans_preview = ans_preview[:120] + "..."
    lines.append(f"    answer       : \"{ans_preview}\"")
    lines.append("")

    lines.append("[8] TIMINGS BREAKDOWN")
    for stage_name, ms in timings.items():
        lines.append(f"    {stage_name:<12}: {ms} ms")
    lines.append("════════════════════════════════════════════════════")

    output_str = "\n".join(lines)
    print(output_str)
    logger.info(output_str)
