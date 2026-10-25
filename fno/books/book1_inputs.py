"""Book 1's inputs on a day (story E5): what D2 reads, gathered from the two packs, the day's canonical A4 snapshot,
the research data B7's live features need, and Book 1's own account. The snapshot must be the one the common pack
records (same snapshot ID and quote-file SHA-256), so the decision reads exactly what the pack froze."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

from ..constants import BOOK1_RULES
from ..desk.common_pack import CommonPack
from ..desk.pack_snapshot import NotThePacksSnapshot, canonical_snapshot
from ..desk.pack_store import PackStore
from ..research_data.quote_snapshots import CutoffSnapshot
from ..research_engine.implied_vol import ImpliedVolModel
from ..risk.inputs import Market
from ..storage.raw_store import RawFileStore
from .book1 import Book1Day, Book1Inputs
from .book1_market import market_from_snapshot


class InputsRefused(ValueError):
    """Book 1's inputs are missing or disagree with the pack: it decides nothing on them."""


class LiveBook1Inputs(Book1Inputs):
    def __init__(self, root: Path, quotes: RawFileStore, rate: float, model: ImpliedVolModel,
                 features: Callable[[date, CutoffSnapshot], object], parts: Callable[[Market], tuple],
                 context: Callable[[date, Mapping[str, str]], Mapping[str, object]]):  # fmt: skip
        self.root, self.quotes, self.rate, self.model = Path(root), quotes, rate, model
        self.features, self.parts, self.context = features, parts, context  # parts(market) -> (book, counts, shadow)

    def day(self, day: date) -> Book1Day:
        packs = PackStore(self.root)
        common = packs.common_path(day)
        if not common.is_file():
            raise InputsRefused(f"no common pack for {day}: Book 1 reads the packs (E2)")
        hashes = {"common_pack_sha256": _sha(common), "private_pack_sha256": _sha(packs.private_path(BOOK1_RULES, day))}
        snapshot = self._snapshot(day, CommonPack.read(day, common))
        market = market_from_snapshot(day, snapshot, self.rate, self.model)
        book, counts, shadow = self.parts(market)
        return Book1Day(market, self.features(day, snapshot), book, counts, shadow, self.context(day, hashes))

    def _snapshot(self, day: date, pack: CommonPack) -> CutoffSnapshot:
        try:
            return canonical_snapshot(day, pack, self.quotes)
        except NotThePacksSnapshot as refused:
            raise InputsRefused(f"{refused}: Book 1 refuses it") from None


def _sha(path: Path) -> str:
    if not path.is_file():
        raise InputsRefused(f"{path.name} of {path.parent.name} is missing: Book 1 reads both packs (E2)")
    return path.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
