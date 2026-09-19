"""Evaluation metrics against hand-computed values, and the runner with a fake retriever."""

import pytest

from app.evaluation.metrics import Retrieved, Source, matches, percentile, question_metrics
from app.evaluation.runner import Question, evaluate


def hit(doc: str, page: int, *entities: str, score: float = 0.5) -> Retrieved:
    return Retrieved(doc, page, page, tuple(entities), score)


def test_relevance_needs_same_document_and_covered_page():
    assert matches(Retrieved("DOC-A", 16, 17, (), 0), Source("DOC-A", 17))  # page range covers 17
    assert not matches(hit("DOC-A", 15), Source("DOC-A", 17))
    assert not matches(hit("DOC-B", 17), Source("DOC-A", 17))
    assert matches(hit("DOC-A", 3), Source("DOC-A", None))  # a source without page: any page


def test_metrics_by_hand():
    sources = [Source("DOC-S", 15), Source("DOC-C", 10)]
    hits = [hit("DOC-X", 1, "E1"), hit("DOC-S", 15, "E2"), hit("DOC-Y", 2), hit("DOC-S", 15), hit("DOC-Z", 9)]
    m = question_metrics(hits, sources, ["E1", "E2", "E3"], k=5)
    assert m["hit"] == 1.0                      # a relevant chunk is in the top 5
    assert m["rr"] == 0.5                       # the first relevant one is at rank 2
    assert m["recall"] == 0.5                   # DOC-S p.15 found, DOC-C p.10 not
    assert m["precision"] == 2 / 5              # ranks 2 and 4 are relevant
    assert m["entity_recall"] == pytest.approx(2 / 3)
    assert question_metrics(hits, sources, [], k=1)["hit"] == 0.0  # rank 1 is not relevant


def test_percentile():
    assert percentile([5, 1, 3, 2, 4], 0.5) == 3
    assert percentile([], 0.9) == 0.0


def test_runner_aggregates_per_category_and_keeps_unanswerable_apart():
    questions = [
        Question("Q1", "about DOC-A", "A", True, [Source("DOC-A", 1)], []),
        Question("Q2", "about DOC-B", "B", True, [Source("DOC-B", 1)], []),
        Question("Q3", "not in the corpus", "H", False, [], []),
    ]

    def retrieve(question: str, k: int) -> list[Retrieved]:
        return [hit("DOC-A", 1, score=0.9)] if "DOC-A" in question else [hit("DOC-Z", 1, score=0.2)]

    result = evaluate(questions, retrieve, k_values=(1, 5))
    assert result["overall"]["1"]["hit"] == 0.5  # Q1 right, Q2 wrong
    assert result["by_category"]["A"]["1"]["hit"] == 1.0 and result["by_category"]["B"]["1"]["hit"] == 0.0
    assert "H" not in result["by_category"]  # unanswerable questions have no relevant source
    assert result["top_score"] == {"answerable_mean": 0.55, "unanswerable_mean": 0.2}
    assert result["questions"] == {"answerable": 2, "unanswerable": 1}
