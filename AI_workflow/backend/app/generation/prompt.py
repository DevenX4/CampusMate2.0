"""The prompt every LLM provider sends. It is provider-independent: switching the model must
not mean rewriting the instructions.

Small models follow short, numbered, concrete rules better than long prose, and use the
sources best when they come right before the question.
"""

from app.generation.base import ABSTAIN_MESSAGE, ContextBlock, GenerationRequest

SYSTEM_PROMPT = f"""You are CampusMate, a conversational campus assistant for Ganpat University (GUNI).
Answer the user's question naturally, concisely, and accurately using ONLY the supplied CampusMate evidence.

Rules:
1. Cite source numbers after important facts using [1], [2], etc.
2. Use conversation context only to understand follow-up references such as "it", "they", "that", "this", "their", etc.
3. If the evidence does not answer the question, reply with exactly this sentence and nothing else:
{ABSTAIN_MESSAGE}
4. Do not invent missing facts, names, dates, room numbers, or policies.
5. Do not mention internal technical details (such as retrieval, embeddings, BM25, RRF, vector databases, or routing).
6. Be direct, natural, and helpful while remaining 100% grounded in the evidence."""

TRUST_LABELS = {"official": "official", "derived_official": "derived from official sources",
                "synthetic": "SYNTHETIC demo data"}


def render_source(block: ContextBlock) -> str:
    return f"[{block.ref}] ({TRUST_LABELS.get(block.source_type, block.source_type)}; {block.label})\n{block.text}"


def render_messages(request: GenerationRequest) -> list[dict[str, str]]:
    sources = "\n\n".join(render_source(block) for block in request.context)
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if request.history:
        for turn in request.history:
            messages.append(turn)
            
    messages.append({
        "role": "user",
        "content": f"Sources:\n\n{sources}\n\nCurrent Question: {request.question}"
    })
    return messages
