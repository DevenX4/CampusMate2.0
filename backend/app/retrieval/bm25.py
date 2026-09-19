"""BM25 lexical ranking, implemented directly so the formula is visible.

For a query Q and a chunk D:

    score(D, Q) = sum over terms q in Q of
                  IDF(q) * f(q, D) * (k1 + 1) / (f(q, D) + k1 * (1 - b + b * |D| / avgdl))

    IDF(q) = ln(1 + (N - n(q) + 0.5) / (n(q) + 0.5))

f(q, D)  how often q occurs in D           |D|    length of D in tokens
N        number of chunks                  avgdl  average chunk length
n(q)     number of chunks containing q
k1       term-frequency saturation (1.2-2.0): the 5th occurrence adds less than the 1st
b        length normalisation (0-1): long chunks do not win just by being long

Rare terms (a course code) weigh a lot; common words ("course") weigh little.
"""

import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass

K1, B = 1.5, 0.75
# Words that carry no meaning for search. IDF already makes them cheap; removing them also
# keeps them from matching every chunk.
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from has have how i in is it its me my of on or "
    "our the their there this to under was what when where which who whom why will with you your".split()
)
# Letters and digits stay together, so "2CEIT78PE7" is ONE token and "COURSE-2CEIT602" gives
# "course" + "2ceit602" (a bare course code then matches the entity ID too).
_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


@dataclass
class Bm25Index:
    ids: list[str]
    lengths: list[int]
    postings: dict[str, dict[int, int]]  # term -> {document index: term frequency}
    avgdl: float

    @classmethod
    def build(cls, ids: list[str], texts: list[str]) -> "Bm25Index":
        postings: dict[str, dict[int, int]] = defaultdict(dict)
        lengths = []
        for index, text in enumerate(texts):
            tokens = tokenize(text)
            lengths.append(len(tokens))
            for term, count in Counter(tokens).items():
                postings[term][index] = count
        return cls(ids, lengths, dict(postings), sum(lengths) / len(lengths) if lengths else 0.0)

    def idf(self, term: str) -> float:
        n = len(self.postings.get(term, {}))
        return math.log(1 + (len(self.ids) - n + 0.5) / (n + 0.5))

    def search(self, query: str, k: int, allowed: Callable[[int], bool] | None = None) -> list[tuple[str, float]]:
        scores: dict[int, float] = defaultdict(float)
        for term in set(tokenize(query)):
            idf = self.idf(term)
            for index, frequency in self.postings.get(term, {}).items():
                if allowed is not None and not allowed(index):
                    continue
                norm = K1 * (1 - B + B * self.lengths[index] / self.avgdl)
                scores[index] += idf * frequency * (K1 + 1) / (frequency + norm)
        best = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:k]
        return [(self.ids[index], score) for index, score in best]
