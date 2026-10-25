"""The daily run's steps (story E3): each reads what earlier steps committed (the pack file, the decisions, the
capture records, the accounts), never memory, so a restarted run continues where it stopped. Each returns its inputs,
its result and the files to commit."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from ..alerts.sender import AlertSender
from ..checks.gate import DataGate
from ..constants import NO_DECISION_LATE
from .common_pack import CommonPack
from .daily_ports import (
    RUN_STOPS,
    AccountSync,
    AccountWriteRefused,
    CommittedDecision,
    DecisionSource,
    ExecutionCapture,
    ExitRules,
    OrderBuilder,
    OrdersRefused,
    Packs,
    StepInterrupted,
    ValidityGate,
    VersionKeeper,
)
from .entries import EntryFiller
from .exits import ExitDesk
from .fill_results import TRADES, trade_entries
from .no_decision import write_no_decision
from .pack_items import PackError
from .timetable import Timetable

NOT_COMMITTED = "nothing visible at the deadline {deadline} (origin {origin})"
COLLECTED_LATE = "collected at {started}, after the deadline {deadline}: no decision can be shown to be on time"
COLLECTION_GRACE = timedelta(seconds=30)  # the step starts at the deadline; later means a restart: fail closed
NO_SNAPSHOT = "no new risk: no valid execution snapshot after the common retry"
NOT_WRITTEN = "not filled: the account write was refused ({reason})"
NOT_ORDERED = "not filled: the committed decision gives no orders ({reason})"
ALERT = "F&O paper desk {day} {book}: {what}"
LATE_AT_SNAPSHOT = "late: committed {committed}, not before the execution snapshot started {started}"
DOUBLE = "{count} original runs ({runs}): only {taken} counts; check why the decision ran twice"
BLOCKED = "no new entry: {why} (today's exits run; the next session opens as usual)"
ENTRY_REFUSED = "trade {trade} not opened: {reason}: information, no action"
NOT_VALIDATED = "not filled: no completed C4 pass ({problems})"


@dataclass(frozen=True)
class StepOutcome:
    inputs: dict
    result: dict
    paths: tuple[Path, ...] = field(default_factory=tuple)


def no_pack(day: date) -> CommonPack:
    """Stands in when no pack could be built: no spot, no snapshot record, so no new trade; exits still run."""
    return CommonPack(day, {"day": day.isoformat(), "kind": "no_pack", "provenance": {}, "items": []})


@dataclass
class DeskSteps:
    root: Path
    books: Sequence[str]
    timetable: Timetable
    versions: VersionKeeper
    packs: Packs
    decisions: DecisionSource
    orders: OrderBuilder
    capture: ExecutionCapture
    gate: DataGate
    validity: ValidityGate
    sync: AccountSync
    entry_desk: EntryFiller
    exit_desk: ExitDesk
    exit_rules: ExitRules
    alerts: AlertSender
    clock: Callable[[], datetime]

    def keep_versions(self, day: date) -> StepOutcome:
        return StepOutcome({}, {"line": self.versions.keep(day)})

    def build_pack(self, day: date) -> StepOutcome:
        try:
            pack = self.packs.build(day)
        except PackError as refused:
            return StepOutcome({}, {"built": False, "reason": str(refused)})
        return StepOutcome({}, {"built": True, "sha256": pack.sha256}, self.packs.files(day))

    def collect_decisions(self, day: date) -> StepOutcome:
        """What the collector observes at the deadline decides who is on time (judge 82): it pulls once and records,
        per book, the run ID and its holding commit, with the origin commit seen. Started after the deadline (a
        restart), it fails closed: every book is late."""
        deadline, started = self.timetable.at(day, self.timetable.decision_deadline), self.clock()
        if started > deadline + COLLECTION_GRACE:
            why = COLLECTED_LATE.format(started=started.isoformat(), deadline=deadline.isoformat())
            return self._all_late(day, deadline, why, {"deadline": deadline.isoformat(), "origin": None})
        origin, result, paths = self.decisions.observe(), {}, []
        for book in self.books:
            decision = self.decisions.committed(book, day, deadline)
            if decision is None:
                why = NOT_COMMITTED.format(deadline=deadline.isoformat(), origin=origin)
                paths.append(write_no_decision(self.root, book, day, deadline, why))
                result[book] = {"decision": NO_DECISION_LATE, "reason": why}
            else:
                result[book] = {"run_id": decision.run_id, "commit": decision.commit,
                                "committed_at": decision.committed_at.isoformat()}  # fmt: skip
            others = self.decisions.others(book, day, decision.run_id if decision else None)
            result[book] |= {"others": others} if others else {}
            self._alert_double(day, book, decision, others)
        return StepOutcome({"deadline": deadline.isoformat(), "origin": origin}, result, tuple(paths))

    def _alert_double(self, day: date, book: str, decision: CommittedDecision | None, others: list[dict]) -> None:
        """ChatGPT review 107: more than one original run of a book on a day (a session fired twice) is one alert; only
        the first counts (D3b), the rest are listed in the run log."""
        originals = [o["run_id"] for o in others if "corrections" not in o] + ([decision.run_id] if decision else [])
        if len(originals) > 1:
            taken = decision.run_id if decision else "none (late)"
            what = DOUBLE.format(count=len(originals), runs=", ".join(sorted(originals)), taken=taken)
            self.alerts.send(ALERT.format(day=day, book=book, what=what))

    def _all_late(self, day: date, deadline: datetime, why: str, inputs: dict) -> StepOutcome:
        paths = tuple(write_no_decision(self.root, book, day, deadline, why) for book in self.books)
        return StepOutcome(inputs, {book: {"decision": NO_DECISION_LATE, "reason": why} for book in self.books}, paths)

    def take_snapshot(self, day: date) -> StepOutcome:
        """One capture for every book; if it is not valid, one common retry for all of them together."""
        attempts = []
        for _ in range(2):
            record = self.capture.capture(day)
            attempts.append(record.snapshot_id if record else None)
            snapshot, report = self.gate.check(self.pack(day))
            if record and snapshot and snapshot.complete and not report.prices_unverified:
                return StepOutcome({}, {"valid": True, "snapshot_id": snapshot.snapshot_id,
                                        "sha256": snapshot.sha256, "attempts": attempts})  # fmt: skip
        return StepOutcome({}, {"valid": False, "attempts": attempts, "reason": NO_SNAPSHOT})

    def pack(self, day: date) -> CommonPack:
        return self.packs.stored(day) or no_pack(day)

    def fill(self, day: date, snapshot_valid: bool, collected: dict, blocked: Mapping[str, str] | None = None
             ) -> StepOutcome:  # fmt: skip
        """Only the runs the decisions step recorded are filled; a book recorded late never fills (judge 82). A book in
        `blocked` (its last session's exits not reviewed, story E2c and review 115) opens nothing new: one alert names
        each such book and why; the other books fill as usual."""
        blocked, inputs = blocked or {}, {"snapshot_valid": snapshot_valid, "decisions": collected}
        if blocked:
            inputs["blocked"] = dict(blocked)
            what = "; ".join(f"{book} {BLOCKED.format(why=why)}" for book, why in blocked.items())
            self.alerts.send(ALERT.format(day=day, book="entries", what=what))
        result: dict = {}
        try:
            self._fill_books(day, snapshot_valid, collected, blocked, result)
        except RUN_STOPS:
            raise
        except Exception as error:  # the trades already written stay in the accounts: the alert says how many
            written = sum(1 for _, _, entry in trade_entries(result) if "snapshot_id" in entry)
            if written:
                raise StepInterrupted(written) from error
            raise
        return StepOutcome(inputs, result)

    def _fill_books(self, day: date, snapshot_valid: bool, collected: dict, blocked: Mapping[str, str], result: dict
                    ) -> None:  # fmt: skip
        """Each book's recorded run filled into `result`, trade by trade, as each is written to its account."""
        pack = self.pack(day)
        for book in self.books:
            entry = collected.get(book, {})
            if book in blocked:
                result[book] = {"outcome": "not filled", "reason": BLOCKED.format(why=blocked[book])}
                continue
            if "run_id" not in entry:
                continue
            decision = self.decisions.recorded(book, day, entry["run_id"], entry["commit"])
            try:
                orders = self.orders.orders(book, decision.run, decision.committed_at)
            except OrdersRefused as refused:  # that book's entries fail closed; the run and every exit go on
                result[book] = {"outcome": "not filled", "reason": NOT_ORDERED.format(reason=refused)}
                self.alerts.send(ALERT.format(day=day, book=book, what=result[book]["reason"]))
                continue
            for order in orders:
                trades = result.setdefault(book, {TRADES: {}})[TRADES]  # by book: two books may share a trade ID
                try:
                    trades[order.proposal.trade_id] = self._fill_one(pack, decision, order, snapshot_valid)
                except AccountWriteRefused as refused:  # never crashes the run before its exits (judge 84)
                    reason = NOT_WRITTEN.format(reason=refused)
                    trades[order.proposal.trade_id] = {"outcome": "not filled", "reason": reason}
                    self.alerts.send(ALERT.format(day=day, book=book, what=reason))

    def _fill_one(self, pack: CommonPack, decision: CommittedDecision, order, snapshot_valid: bool) -> dict:
        if not snapshot_valid:
            return {"outcome": "not filled", "reason": NO_SNAPSHOT}
        problems = self.validity.problems(decision, order)
        if problems:
            return {"outcome": "not filled", "reason": NOT_VALIDATED.format(problems="; ".join(problems))}
        snapshot, report = self.gate.check(pack, order.contracts())
        if snapshot is None:
            return {"outcome": "not filled", "reason": report.reason()}
        if decision.committed_at >= snapshot.started_at:
            late = LATE_AT_SNAPSHOT.format(committed=decision.committed_at, started=snapshot.started_at)
            return {"outcome": "not filled", "reason": late}
        message = f"desk fills {order.book} {order.proposal.trade_id}"
        entered = self.sync.write(order.book, lambda j: self.entry_desk.enter(order, snapshot, j, report), message)
        if entered.refused_by_check:  # story E4c: refused before any fill, for information; once, never on a replay
            what = ENTRY_REFUSED.format(trade=entered.trade_id, reason=entered.reason)
            # an unsent alert is printed once by the daily run's one sender (story O1's `ReportedAlerts`)
            self.alerts.send(ALERT.format(day=snapshot.day, book=order.book, what=what))
        return {"outcome": entered.outcome, "reason": entered.reason, "snapshot_id": snapshot.snapshot_id,
                "sha256": snapshot.sha256}  # fmt: skip

    def review_exits(self, day: date) -> StepOutcome:
        """Risk-reducing exits run whatever happened to the decisions or the snapshot (design 9), book by book: one
        book's failure is recorded and alerted, and never stops another book's review (judge 84)."""
        pack, result = self.pack(day), {}
        for book in self.books:
            try:
                result[book] = self._review_book(pack, book, day)
            except Exception as failure:  # noqa: BLE001 - any failure of one book must not halt the others' exits
                result[book] = {"reviewed": False, "error": f"{type(failure).__name__}: {failure}"}
                self.alerts.send(ALERT.format(day=day, book=book, what=f"EXIT REVIEW FAILED: {result[book]['error']}"))
        return StepOutcome({}, result)

    def _review_book(self, pack: CommonPack, book: str, day: date) -> dict:
        rules = self.exit_rules.rules(book)
        snapshot, report = self.gate.check(pack)
        if snapshot is None:  # no desk event without a snapshot: the gate's alert names the exits held up
            due = self.sync.write(book, lambda j: self.exit_desk.due_exits(j, day, rules), f"exit check {book}")
            self.gate.check(pack, due_exits=due)
            return {"reviewed": False, "waiting": due, "reason": report.reason()}
        message = f"desk exits {book}"
        reviewed = self.sync.write(book, lambda j: self.exit_desk.review(book, snapshot, j, rules, report), message)
        return {"reviewed": True, "results": [{"trade_id": r.trade_id, "outcome": r.outcome, "reason": r.reason}
                                              for r in reviewed]}  # fmt: skip
