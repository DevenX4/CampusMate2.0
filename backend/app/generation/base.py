"""The contract between CampusMate and whatever writes the answer.

The rest of the application depends only on GenerationProvider. Which model (or no model)
produces the text is a configuration choice, so the SLM can be replaced without touching the
router, the evidence or the chat API.

A provider receives the question and numbered context blocks; the answer cites them as [1],
[2]. It does not decide what is true: the evidence was chosen before it is called, and the
grounding validator checks its output afterwards.
"""

from dataclasses import dataclass
from typing import Protocol

# The one answer for "the knowledge base does not say". Providers and the chat API use the
# same sentence, so an abstention is recognisable (and testable) whatever produced it.
ABSTAIN_MESSAGE = "I couldn't find authoritative information for that in the current CampusMate knowledge base."


class GenerationError(Exception):
    """The provider could not produce an answer (server down, timeout, bad response)."""


@dataclass(frozen=True)
class ContextBlock:
    ref: int  # the number the answer cites: [ref]
    kind: str  # structured | graph | document
    source_type: str  # official | derived_official | synthetic
    label: str  # human-readable source, e.g. "Syllabus 2021-22, p.15"
    text: str


@dataclass(frozen=True)
class GenerationRequest:
    question: str
    context: list[ContextBlock]
    max_tokens: int = 400
    temperature: float = 0.0


@dataclass(frozen=True)
class GenerationResult:
    text: str
    provider: str
    model: str
    latency_ms: int
    prompt_tokens: int | None = None  # reported by LLM servers; None for the extractive provider
    completion_tokens: int | None = None


class GenerationProvider(Protocol):
    name: str
    model: str

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Write an answer from request.context only. Raises GenerationError."""
        ...

    def check(self) -> str:
        """Verify the provider is usable (server reachable, model present) and describe it.
        Raises GenerationError."""
        ...
