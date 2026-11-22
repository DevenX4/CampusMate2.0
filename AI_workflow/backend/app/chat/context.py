"""Context builder: turns the gathered evidence into the numbered sources the answer cites.

It decides what the generator sees, within a budget. A small model reads a 4,096-token window
at most: about 6,000 characters of sources (roughly 1,500-2,000 tokens) leave room for the
rules and a 400-token answer. Structured facts come first, then at most a few graph items,
then document passages, in the order the router ranked them.
"""

from dataclasses import dataclass

from app.generation.base import ContextBlock
from app.routing.evidence import Evidence

MAX_BLOCKS = 8
MAX_GRAPH_BLOCKS = 3
MAX_CONTEXT_CHARS = 6000
MAX_BLOCK_CHARS = 1500
OFFICIAL_TYPES = ("official", "derived_official")


@dataclass
class Context:
    blocks: list[ContextBlock]
    evidence: dict[int, Evidence]  # ref -> the evidence behind [ref], for citations


def label(evidence: Evidence) -> str:
    c = evidence.citation
    pages = f"p.{c.page_start}" if c.page_end in (None, c.page_start) else f"pp.{c.page_start}-{c.page_end}"
    where = f"{c.document_id}, {pages}" if c.page_start is not None else c.document_id
    return f"{where} ({c.title})" if c.title else where


def _clip(text: str) -> str:
    return text if len(text) <= MAX_BLOCK_CHARS else text[:MAX_BLOCK_CHARS].rsplit(" ", 1)[0] + " ..."


def build_context(evidence: list[Evidence], official_only: bool = False) -> Context:
    blocks: list[ContextBlock] = []
    by_ref: dict[int, Evidence] = {}
    seen: set[str] = set()
    used_chars = graph_blocks = 0
    for item in evidence:
        if official_only and item.source_type not in OFFICIAL_TYPES:
            continue  # the user asked for official information only
        text = _clip(item.text.strip())
        if not text or text in seen:
            continue
        if item.kind == "graph" and graph_blocks == MAX_GRAPH_BLOCKS:
            continue
        if used_chars + len(text) > MAX_CONTEXT_CHARS:
            continue  # a later, shorter item may still fit
        ref = len(blocks) + 1
        blocks.append(ContextBlock(ref, item.kind, item.source_type, label(item), text))
        by_ref[ref] = item
        seen.add(text)
        used_chars += len(text)
        graph_blocks += item.kind == "graph"
        if len(blocks) == MAX_BLOCKS:
            break
    return Context(blocks, by_ref)
