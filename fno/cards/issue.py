"""Issuing a built card (story T1): post it, check the host clock against Slack's and GitHub's server times, save the
full card record to Drive, then write the non-sensitive delivery metadata for the repository. Each step's failure is a
printed line and a stored fact, never a stop: the card is posted first, so a Drive outage cannot hold it back."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from ..server_clock import SkewCheck, unchecked, utc_text
from .card import TradeCard
from .card_clocks import CardClocks, ClockChecks
from .deliveries import DeliveryLog
from .minimal_facts import FACTS_FAILED, NOT_JSON, minimal_facts
from .posting import CardPoster, PostReceipt
from .record_store import NOT_SAVED, CardRecordStore

RECORD_SCHEMA, DELIVERY_SCHEMA = "card_record/v1", "card_delivery/v1"
CLOCKS = "the clocks"
RECORD_NOT_BUILT = "record not built ({error})"
TEST_BANNER = "TEST — PAPER ONLY: a one-off check of live delivery, not the day's card."
NOT_WRITTEN = "delivery metadata NOT written ({error}); commit it by hand:\n{metadata}"
WRITTEN = "delivery metadata written: {path} (commit and push it: its push receipt is the second issuance witness)"


@dataclass(frozen=True)
class IssueResult:
    lines: tuple[str, ...]  # what to print
    sent: bool
    complete: bool  # every stage after the post succeeded: the Drive record saved, the metadata written (T1f)


def card_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class CardIssuer:
    def __init__(
        self, poster: CardPoster, records: CardRecordStore, deliveries: DeliveryLog, clocks: CardClocks,
        host_now: Callable[[], datetime], code_commit: str,
    ):  # fmt: skip
        self.poster, self.records, self.deliveries = poster, records, deliveries
        self.clocks, self.host_now, self.code_commit = clocks, host_now, code_commit

    def issue(self, card: TradeCard, text: str, test: bool = False) -> IssueResult:
        """`test`: the one live delivery check (T1 criterion 16): marked on its first line and in both records, and
        never counted as the session's card. After the post every stage is guarded on its own (story T1f), so a
        raise in one never skips the next and the post always leaves its records, or says plainly why not."""
        text = f"{TEST_BANNER}\n{text}" if test else text
        before = self.host_now()
        receipt = self.poster.post(text)
        after = self.host_now()
        clocks = self._clocks(receipt, before, after)
        try:
            facts, failed = {**self._facts(card, text, receipt, before, after, clocks.checks), "test": test}, False
        except Exception as error:  # noqa: BLE001 - the card is out: keep what is plainly known (T1f stage 2)
            facts, failed = self._minimal(card, text, receipt, clocks, test, FACTS_FAILED, error), True
        saved, drive_line = self._save(card, text, facts, receipt, after, test)
        delivery = {**facts, "schema": DELIVERY_SCHEMA, "drive": {"saved": saved, "outcome": drive_line}}
        fallback = {**self._minimal(card, text, receipt, clocks, test, NOT_JSON), "schema": DELIVERY_SCHEMA,
                    "drive": delivery["drive"]}  # fmt: skip
        written, delivery_line = self._write(card, delivery, fallback)
        lines = (receipt.outcome, *(c.line for c in clocks.checks), drive_line, delivery_line)
        return IssueResult(lines, receipt.sent, saved and written and not (failed or clocks.failed))

    def _clocks(self, receipt: PostReceipt, before: datetime, after: datetime) -> ClockChecks:
        try:
            return self.clocks.check(receipt, before, after)
        except Exception as error:  # noqa: BLE001 - a broken clock form is a named miss, never a lost record
            return ClockChecks((unchecked(CLOCKS, type(error).__name__),), (CLOCKS,))

    def _save(self, card, text, facts: dict, receipt: PostReceipt, after: datetime, test: bool) -> tuple[bool, str]:
        """The Drive record is built inside the same guard as its save (judge 592: a raise in either is one miss)."""
        try:
            record = {**facts, "schema": RECORD_SCHEMA, "text": text, "warning": _warning(card),
                      "sections": [_section(s) for s in card.sections]}  # fmt: skip
            name = _record_name(card, receipt, after) + ("_test" if test else "")
            return self.records.save(card.day, name, _json(record))
        except Exception as error:  # noqa: BLE001 - the card is out: the metadata below still says so
            return False, NOT_SAVED.format(reason=RECORD_NOT_BUILT.format(error=type(error).__name__))

    def _minimal(self, card, text, receipt, clocks: ClockChecks, test: bool, why: str, error=None) -> dict:
        name = type(error).__name__ if error else "{error}"
        return minimal_facts(card, text, receipt, clocks.checks, self.code_commit, test, why.format(error=name))

    def _write(self, card: TradeCard, delivery: dict, fallback: dict) -> tuple[bool, str]:
        try:
            return True, WRITTEN.format(path=self.deliveries.write(card.day, delivery))
        except Exception as error:  # noqa: BLE001 - the post is out: print the metadata to commit by hand
            return False, NOT_WRITTEN.format(error=type(error).__name__, metadata=_printable(delivery, fallback))

    def _facts(self, card, text, receipt: PostReceipt, before, after, checks: Sequence[SkewCheck]) -> dict:
        """What both the Drive record and the delivery metadata hold (no card text: that goes to Drive only)."""
        slack_time = receipt.server_time
        return {
            "day": card.day.isoformat(), "status": str(card.status), "reason_code": card.reason_code,
            "card_sha256": card_sha256(text), "code_commit": self.code_commit,
            "records_used": [{"path": r.path, "sha256": r.sha256} for r in card.used],
            "missing": list(card.missing), "previous_misses": list(card.previous_misses),
            "slack": {
                "sent": receipt.sent, "ts": receipt.ts, "channel": receipt.channel, "outcome": receipt.outcome,
                "server_time_utc": utc_text(slack_time) if slack_time else None,
            },
            "host_clock": {"before_utc": utc_text(before), "after_utc": utc_text(after)},
            "clock": [c.stored() for c in checks],
        }  # fmt: skip


def _printable(delivery: dict, fallback: dict) -> str:
    """The metadata as JSON, or the minimal facts if it cannot be (T1f stage 4): still readable by the next card."""
    try:
        return _json(delivery).decode("utf-8")
    except Exception as error:  # noqa: BLE001 - plain values only from here on, so this always turns into JSON
        return _json({**fallback, "failure": fallback["failure"].format(error=type(error).__name__)}).decode("utf-8")


def _section(section) -> dict:
    return {"title": section.title, "lines": list(section.lines), "missing": list(section.missing)}


def _warning(card: TradeCard) -> dict | None:
    """Story T1e: the warning kept as data in the Drive record (never in the repository's delivery metadata)."""
    return {"headline": card.warning.headline, "detail": card.warning.detail} if card.warning else None


def _record_name(card: TradeCard, receipt: PostReceipt, after: datetime) -> str:
    """Slack's ts names a sent card; an unsent one is named by the host's UTC time (each attempt its own file)."""
    stamp = receipt.ts.replace(".", "") if receipt.ts else f"unsent-{after.astimezone(UTC):%H%M%S%f}"
    return f"{card.day.isoformat()}_{stamp}"


def _json(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode("utf-8")
