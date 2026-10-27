"""How alike two titles are (P2c), behind an interface: a better measure is one new class and a line in `cluster.py`.

**The numbers below are defaults, not findings.** No real news has been collected yet (the first real fetch is the
owner's go-live), so the threshold and the entity step are reasoning only, tested on invented pairs: that proves the
code obeys the rule and says nothing about whether the threshold is right for real news. Until they are re-tuned from
the first week of real polls, nothing derived from clusters (corroboration, a story count, "how many outlets carried
it") may be trusted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

THRESHOLD = 0.55  # a title pair at or above this is the same story (reasoning only, untuned)
ENTITY_STEP = 0.10  # a shared entity lowers the bar by this; two different entities raise it (reasoning only, untuned)


class Similarity(ABC):
    @abstractmethod
    def score(self, a: frozenset[str], b: frozenset[str]) -> float:
        """0.0 (nothing shared) to 1.0 (the same shingles)."""


class Jaccard(Similarity):
    def score(self, a: frozenset[str], b: frozenset[str]) -> float:
        union = len(a | b)
        return len(a & b) / union if union else 0.0
