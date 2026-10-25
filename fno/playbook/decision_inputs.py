"""Everything one day's D2 evaluation read, captured while it reads it (story D3), so the decision can be replayed:
the playbook files and registry as they stood (with the commit they were read at), the market, the live feature values
per decision context, the book, its trade counts and each shadow account. The live run wraps its real sources in the
`Recording*` adapters; a replay feeds D2 the `Replayed*` ones built from the stored JSON."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ..research_engine.features import DecisionContext, FeatureValue
from .allocation import StrategyTradeCounts
from .decision_codec import book_from_json, book_to_json, market_from_json
from .documents import strategy_from_text
from .evaluate import LiveFeatureValues
from .loader import Playbook
from .registry import parse_rows
from .schema import Strategy
from .shadow import ShadowAccount, ShadowBooks


def context_key(context: DecisionContext) -> str:
    return f"{context.expiry.isoformat()}|{context.entry_day.isoformat()}|{context.exit_day.isoformat()}"


def strategy_key(name: str, version: int) -> str:
    return f"{name}-v{version}"


class RecordingFeatures(LiveFeatureValues):
    def __init__(self, inner: LiveFeatureValues):
        self.inner, self.seen = inner, {}

    def values(self, day: date, context: DecisionContext) -> Mapping[str, FeatureValue]:
        key = context_key(context)
        if key not in self.seen:
            self.seen[key] = dict(sorted(self.inner.values(day, context).items()))
        return self.seen[key]


class ReplayedFeatures(LiveFeatureValues):
    def __init__(self, seen: Mapping[str, Mapping[str, FeatureValue]]):
        self.seen = seen

    def values(self, day: date, context: DecisionContext) -> Mapping[str, FeatureValue]:
        return self.seen[context_key(context)]  # a context the live run never asked for is a replay error


class RecordingCounts:
    def __init__(self, inner: StrategyTradeCounts):
        self.inner, self.seen = inner, {}

    def _get(self, name: str, version: int) -> dict:
        key = strategy_key(name, version)
        if key not in self.seen:
            self.seen[key] = {"completed": self.inner.completed(name, version), "open": self.inner.open(name, version)}
        return self.seen[key]

    def completed(self, name: str, version: int) -> int:
        return self._get(name, version)["completed"]

    def open(self, name: str, version: int) -> int:
        return self._get(name, version)["open"]


class ReplayedCounts:
    def __init__(self, seen: Mapping[str, Mapping[str, int]]):
        self.seen = seen

    def completed(self, name: str, version: int) -> int:
        return self.seen[strategy_key(name, version)]["completed"]

    def open(self, name: str, version: int) -> int:
        return self.seen[strategy_key(name, version)]["open"]


class RecordingShadowBooks(ShadowBooks):
    def __init__(self, inner: ShadowBooks):
        self.inner, self.seen = inner, {}

    def account(self, strategy: Strategy) -> ShadowAccount:
        account = self.inner.account(strategy)
        counts = RecordingCounts(account.counts)
        counts.completed(*strategy.key)  # the shadow allocator asks these two; record them up front
        self.seen[strategy_key(*strategy.key)] = (account, counts)
        return ShadowAccount(account.book, counts, account.storage)

    def to_json(self) -> dict:
        return {
            key: {"book": book_to_json(account.book), "counts": counts.seen, "storage": str(account.storage)}
            for key, (account, counts) in sorted(self.seen.items())
        }


class ReplayedShadowBooks(ShadowBooks):
    def __init__(self, seen: Mapping[str, Mapping]):
        self.seen = seen

    def account(self, strategy: Strategy) -> ShadowAccount:
        stored = self.seen[strategy_key(*strategy.key)]
        return ShadowAccount(book_from_json(stored["book"]), ReplayedCounts(stored["counts"]), Path(stored["storage"]))


@dataclass(frozen=True)
class PlaybookSnapshot:
    """The playbook as the day's run read it: each version file's text, the registry's text and the commit read."""

    files: Mapping[str, str]
    registry_csv: str
    commit: str

    def playbook(self) -> Playbook:
        strategies = tuple(strategy_from_text(text, name) for name, text in sorted(self.files.items()))
        return Playbook(strategies, tuple(parse_rows(self.registry_csv)))


@dataclass(frozen=True)
class DayInputs:
    day: date
    playbook: PlaybookSnapshot
    market: dict  # market_to_json
    features: dict = field(default_factory=dict)
    book: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)
    shadow: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "day": self.day.isoformat(),
            "playbook": {"files": dict(sorted(self.playbook.files.items())), "registry_csv": self.playbook.registry_csv,
                         "commit": self.playbook.commit},  # fmt: skip
            "market": self.market, "features": self.features, "book": self.book, "counts": self.counts,
            "shadow": self.shadow,
        }  # fmt: skip

    @classmethod
    def from_json(cls, data: dict) -> DayInputs:
        snapshot = PlaybookSnapshot(
            data["playbook"]["files"], data["playbook"]["registry_csv"], data["playbook"]["commit"]
        )
        return cls(date.fromisoformat(data["day"]), snapshot, data["market"], data["features"], data["book"],
                   data["counts"], data["shadow"])  # fmt: skip

    def replay_arguments(self) -> tuple:
        """The arguments of `RuleEvaluator.evaluate`, rebuilt from the stored inputs."""
        return (
            self.day, self.playbook.playbook(), market_from_json(self.market), ReplayedFeatures(self.features),
            book_from_json(self.book), ReplayedCounts(self.counts), ReplayedShadowBooks(self.shadow),
        )  # fmt: skip
