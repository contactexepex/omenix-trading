"""One scorecard run (story E6): load the playbook, read every account's records, fire the automatic pauses, then build
the scorecards asked for. Pauses always look at every account (a filter only narrows what is shown), so a loss in
any book pauses the version for all of them."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date

from ..constants import PlaybookStatus
from ..desk.records import DeskRecords
from ..desk.snapshot import ContractKey, ExecutionSnapshotSource
from ..desk.trade_counts import version_key
from ..playbook.loader import Playbook, PlaybookLoader
from .pauses import AutoPauser, catastrophic_losses, cumulative_losses, drifts
from .review import ReviewTerms
from .scorecard import Scorecard, build_scorecard
from .strategy_record import StrategyRecord, strategy_records


class ScorecardRun:
    def __init__(self, accounts: Callable[[], Sequence[str]], records_of: Callable[[str], DeskRecords],
                 loader: PlaybookLoader, pauser: AutoPauser, charges: Mapping[str, float],
                 terms: ReviewTerms, snapshots: ExecutionSnapshotSource):  # fmt: skip
        self.accounts, self.records_of, self.loader, self.pauser = accounts, records_of, loader, pauser
        self.charges, self.terms, self.snapshots = dict(charges), terms, snapshots

    def run(self, on: date, marks: Mapping[ContractKey, float], account: str | None = None,
            strategy: str | None = None, pause: bool = True) -> tuple[list[Scorecard], list[str]]:  # fmt: skip
        """(scorecards, one line per automatic pause or alert)."""
        playbook = self.loader.load()
        records = [r for name in self.accounts() for r in strategy_records(name, self.records_of(name), self.charges)]
        actions = []
        if pause:
            approved_on = {r.key: r.changed_on for r in self.loader.registry.rows() if r.status == PlaybookStatus.PAPER}
            triggers = drifts(playbook) + catastrophic_losses(records, playbook, on, approved_on)
            triggers += cumulative_losses(records, playbook, on, approved_on)
            actions = self.pauser.apply(triggers, playbook, on)
            playbook = self.loader.load() if actions else playbook
        shown = [r for r in records if account in (None, r.account) and strategy in (None, r.strategy)]
        return [
            build_scorecard(r, _version(playbook, r), on, marks, self.terms, self.snapshots) for r in shown
        ], actions


def _version(playbook: Playbook, record: StrategyRecord):
    key = version_key(record.strategy)
    return next((s for s in playbook.strategies if s.key == key), None)
