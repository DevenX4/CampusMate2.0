"""Hallucination regression tests: the 23 trap questions of the dataset (real contacts, entities
that do not exist, "official" questions only synthetic data could answer, details the sources
do not contain), asked through the whole pipeline with every real PDF ingested.

The rule (evaluation/datasets/negative_questions.json): abstain, or answer only from the sources
and label demo data as demo data. See trap_violations in app/evaluation/answers.py.
"""

import pytest

from app.chat.pipeline import answer_question
from app.core.config import REPO_ROOT, get_settings
from app.evaluation.answers import load_traps, trap_violations
from app.generation.base import ABSTAIN_MESSAGE
from app.generation.extractive import ExtractiveProvider
from app.ingestion.pipeline import process_next
from app.retrieval.search import Bm25Cache
from app.routing.evidence import RetrievalDeps
from app.seed.run import seed
from app.services.ingestion_jobs import queue_missing
from tests.helpers import make_indexer

TRAPS = load_traps(REPO_ROOT / "evaluation" / "datasets" / "negative_questions.json")


@pytest.fixture(scope="module")
def ask(seeded_session, tmp_path_factory):
    storage = tmp_path_factory.mktemp("storage")
    seed(seeded_session, get_settings().data_dir, storage)  # copies the 12 PDFs into this storage
    assert queue_missing(seeded_session) == 12
    indexer = make_indexer(storage / "chroma")
    while process_next(seeded_session, storage, max_chars=1200, lease_minutes=30, indexer=indexer):
        pass
    deps = RetrievalDeps(indexer.embedder, indexer.index, Bm25Cache())
    return lambda question: answer_question(seeded_session, question, deps, ExtractiveProvider())


@pytest.mark.parametrize("trap", TRAPS, ids=[t.question_id for t in TRAPS])
def test_trap_is_abstained_or_answered_honestly(ask, trap):
    answer = ask(trap.text)
    assert trap_violations(trap, answer) == [], answer.answer


def test_a_wrapped_disclaimer_is_not_turned_into_its_opposite(ask):
    # NEG-003 once quoted "an actual Ganpat University schedule" from "... are not / an actual
    # Ganpat University schedule." (a PDF line wrap).
    answer = ask("What is the actual 2027 examination schedule at Ganpat University?")
    assert not answer.answer.startswith("(Synthetic demo data) an actual")
    assert answer.answer == ABSTAIN_MESSAGE or "are not an actual Ganpat University schedule" in answer.answer
