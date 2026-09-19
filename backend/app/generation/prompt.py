"""The prompt every LLM provider sends. It is provider-independent: switching the model must
not mean rewriting the instructions.

Small models follow short, numbered, concrete rules better than long prose, and use the
sources best when they come right before the question.
"""

from app.generation.base import ABSTAIN_MESSAGE, ContextBlock, GenerationRequest

SYSTEM_PROMPT = f"""You are CampusMate, the campus assistant of the Information Technology department of Ganpat University (GUNI).
Answer the question using ONLY the numbered sources you are given.

Rules:
1. After every fact, cite the number of the source it comes from, like [1] or [2][3].
2. If the sources do not answer the question, reply with exactly this sentence and nothing else:
{ABSTAIN_MESSAGE}
3. Sources marked SYNTHETIC are demo data, not official GUNI information. If you use one, say it is demo data.
4. Copy numbers, course codes and names exactly as they appear in the sources. Never guess, round or add facts.
5. Be brief: at most five sentences, or a short list."""

TRUST_LABELS = {"official": "official", "derived_official": "derived from official sources",
                "synthetic": "SYNTHETIC demo data"}


def render_source(block: ContextBlock) -> str:
    return f"[{block.ref}] ({TRUST_LABELS.get(block.source_type, block.source_type)}; {block.label})\n{block.text}"


def render_messages(request: GenerationRequest) -> list[dict[str, str]]:
    sources = "\n\n".join(render_source(block) for block in request.context)
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Sources:\n\n{sources}\n\nQuestion: {request.question}"}]
