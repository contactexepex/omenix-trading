"""Per road, the share of scheduled decisions refused for quotes (story MS-P1j, orchestrator 22 Oct 2026): law 5's four
reasons, read from each record's own law results (a refusal named by a stop still counts here when a quote law also
refused). The capture gate's band is about 10 steps while the shorts sit about 20 out, so thin far legs stay visible.

The "why refused" breakdown counts every reason a decision carried (Judge I's note, orchestrator 22 Oct 2026): the
three counts use the one named refusal per decision so their totals add up, while this line shows a risk law that
failed only because a quote was missing as the consequence it is. It is labelled so nobody sums it to decisions.

Margin-not-checked refusals are counted by their cause, the cause's name only: a law result's note can name a
contract or a leg (MS-P1m's causes do), so a note is never quoted and never leaves the dashcam (judge 494)."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from ..constants import NoTradeReason, RoadCode
from ..contracts.records import DecisionRecord
from ..safety.margin_law import MARGIN_NOT_CHECKED, margin_not_checked
from ..safety.quote_laws import GATE_REASONS


@dataclass(frozen=True)
class QuoteShare:
    road: RoadCode
    scheduled: int
    quote_refused: int
    driver_stops: int = 0  # decisions the driver ended itself with no_valid_quotes (no law result is involved)

    @property
    def share(self) -> float:
        return self.quote_refused / self.scheduled if self.scheduled else 0.0


def quote_shares(records: Iterable[DecisionRecord]) -> tuple[QuoteShare, ...]:
    scheduled, refused, stopped = Counter(), Counter(), Counter()
    for record in records:
        scheduled[record.road] += 1
        law_refused = any(not r.passed and r.reason in GATE_REASONS for r in record.law_results)
        refused[record.road] += law_refused
        stopped[record.road] += not law_refused and _driver_stopped_for_quotes(record)
    return tuple(QuoteShare(road, scheduled[road], refused[road], stopped[road]) for road in sorted(scheduled))


def _driver_stopped_for_quotes(record: DecisionRecord) -> bool:
    """A driver that finds no valid quotes proposes nothing, so no law runs: counted from the decision itself. The
    reason is a no-trade reason only (`Decision` refuses it under any other outcome), so it alone names the case."""
    return record.decision.reason == NoTradeReason.NO_VALID_QUOTES


def margin_unchecked_causes(records: Iterable[DecisionRecord]) -> Counter:
    """(road, cause name) -> count; the cause name is the note's text after the prefix up to its first colon."""
    causes = Counter()
    for record in records:
        for result in record.law_results:
            if margin_not_checked(result):
                causes[(record.road, cause_name(result.note))] += 1
    return causes


def cause_name(note: str) -> str:
    return note.removeprefix(MARGIN_NOT_CHECKED).split(":", 1)[0].strip()


def reason_counts(records: Iterable[DecisionRecord]) -> Counter:
    """(road, reason) -> the number of decisions that carried that refusal among their law results."""
    counts = Counter()
    for record in records:
        for reason in {r.reason for r in record.law_results if not r.passed and r.reason is not None}:
            counts[(record.road, reason)] += 1
    return counts


QUOTE_LINE = "{road}: {refused} of {scheduled} refused for quotes ({share:.0%})"
DRIVER_STOPS_SUFFIX = "; {stopped} more ended no_valid_quotes in the driver"  # only when there are any
MARGIN_LINE = "{road}: margin not checked ({cause}) x{count}"
REASONS_LINE = "{road}: refusal reasons, a decision can have several: {reasons}"


def share_lines(records: tuple[DecisionRecord, ...]) -> tuple[str, ...]:
    """Counts only, for the run's printout and the reports."""
    lines = [QUOTE_LINE.format(road=s.road, refused=s.quote_refused, scheduled=s.scheduled, share=s.share)
             + (DRIVER_STOPS_SUFFIX.format(stopped=s.driver_stops) if s.driver_stops else "")
             for s in quote_shares(records)]  # fmt: skip
    causes = sorted(margin_unchecked_causes(records).items())
    lines += [MARGIN_LINE.format(road=road, cause=cause, count=n) for (road, cause), n in causes]
    by_road: dict = {}
    for (road, reason), n in sorted(reason_counts(records).items()):
        by_road.setdefault(road, []).append(f"{reason} x{n}")
    lines += [REASONS_LINE.format(road=road, reasons=", ".join(reasons)) for road, reasons in by_road.items()]
    return tuple(lines)
