"""The paired rows over sealed decisions (story MS-INS, part e): each scheduled decision's road-slot, the decisions
h's counting rule counts (judged at the commit that sealed them), and each driver version against N0, RC1 and REF on
their common counted road-days. RC1 against N0 is the live null, printed in every review."""

from collections import Counter, defaultdict
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date

from ....models import IST
from ...constants import SLOT_1500, DriverRole, RecordKind
from ...contracts.dashcam import DashcamStore
from ...contracts.decisions import DriverCard
from ...contracts.records import DecisionRecord
from ...contracts.seal import StaleSeal
from ...registration.clusters import common_road_days
from ...registration.counting import CountCandidate, CountingRule
from ..contracts import HeldPath, PairedRow
from ..paired.compare import compare
from ..paired.values import road_slot

CONTROL_CODES = ("N0", "RC1", "REF")
NULL_PAIR = ("RC1", "N0")


@dataclass(frozen=True)
class SealedDecisions:
    records: tuple[tuple[DecisionRecord, str], ...]  # each with the commit of its seal
    unsealed: tuple[date, ...]  # trading sessions with no decisions file, or a damaged one

    def outcome_counts(self) -> dict[str, Counter]:
        """Every scheduled decision's outcome code, by driver: the denominator of every count, refusals included."""
        counts: dict[str, Counter] = defaultdict(Counter)
        for record, _ in self.records:
            counts[record.decision.driver_id][record.decision.outcome.value] += 1
        return dict(counts)


def sealed_decisions(dashcam: DashcamStore, sessions: Collection[date]) -> SealedDecisions:
    records, unsealed = [], []
    for session in sessions:
        seal = dashcam.find(session, SLOT_1500, RecordKind.DECISIONS)
        try:
            found = dashcam.read(seal) if seal else None
        except StaleSeal:
            found = None
        if found is None:
            unsealed.append(session)
            continue
        records += [(r, seal.commit) for r in found if isinstance(r, DecisionRecord)]
    return SealedDecisions(tuple(records), tuple(unsealed))


class CountedComparison:
    def __init__(self, counting: CountingRule, cards: Mapping[str, DriverCard], rules_sha256: str):
        self.counting, self.cards, self.rules_sha256 = counting, cards, rules_sha256

    def rows(self, decisions: SealedDecisions, closed: Collection[HeldPath],
             unfilled: Collection = frozenset()) -> tuple[PairedRow, ...]:  # fmt: skip
        """`unfilled`: (driver, road, session) of fired entries that never filled, when the fleet reports them."""
        outcomes = {(p.outcome.driver_id, p.outcome.road, p.outcome.entry.filled_at.astimezone(IST).date()): p.outcome
                    for p in closed}  # fmt: skip
        slots: dict[str, dict] = defaultdict(dict)
        counted = []
        for record, commit in decisions.records:
            slots[record.decision.driver_id][(record.session, record.road)] = road_slot(record, outcomes, unfilled)
            candidate = CountCandidate(record.session, record.road, record.decision.driver_id, record.card_sha256,
                                       commit)  # fmt: skip
            counted += [candidate] if self.counting.verdict(candidate).counted else []
        controls = [self.cards[c] for c in CONTROL_CODES if c in self.cards]
        rows = []
        for card in self._drivers():
            targets = [self.cards[NULL_PAIR[1]]] if card.code == NULL_PAIR[0] else controls
            pairs = [(card, c) for c in targets]
            common = {
                (d.driver_id, c.driver_id): common_road_days(counted, [d.driver_id, c.driver_id]) for d, c in pairs
            }
            rows += compare(card, [c for _, c in pairs], self.cards.values(), slots, common, self.rules_sha256)
        return tuple(rows)

    def _drivers(self) -> list[DriverCard]:
        """Every rule and measurement-only driver, then RC1 as the live null (against N0 only)."""
        drivers = [c for c in self.cards.values() if c.role != DriverRole.CONTROL]
        null, n0 = self.cards.get(NULL_PAIR[0]), self.cards.get(NULL_PAIR[1])
        return drivers + ([null] if null and n0 else [])
