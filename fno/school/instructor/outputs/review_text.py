"""The 30-session review as text (story MS-INS, part e): every driver's denominators first, then its rupees, its
attribution and causes, then every paired row with its notes, then what could not be read. Labelled descriptive,
paper only; the plain P2 line is printed first (orchestrator's condition 4)."""

from ..contracts import Cause
from .labels import cause_words
from .review import DriverSummary, Review

HEADER = ("Market school instructor, descriptive review {first} to {last} ({sessions} sessions)."
          " PAPER ONLY: no claim, no licence.")  # fmt: skip
P2_LINE = ("At this sample size every driver reads Exploratory or Not established for any realistic edge; an edge of"
           " Rs 300 a trade would need many years to show.")  # fmt: skip
ROW = ("  vs {control} ({measure}): {status}; {sessions} sessions, {road_slots} road-slots; mean {mean}; bound {bound};"
       " batch {batch}; abstentions {da}/{ca}; unavailable {un}; after the cut {cut}; {note}")  # fmt: skip


def review_lines(review: Review) -> list[str]:
    lines = [HEADER.format(first=review.first, last=review.last, sessions=len(review.sessions)), P2_LINE]
    for driver in review.drivers:
        lines += _driver(driver)
        lines += [_row(r) for r in review.paired if r.driver_id == driver.driver_id]
    lines.append(f"Unreadable outcomes files: {_days(review.unreadable)}; sessions without readable decisions:"
                 f" {_days(review.unsealed)}; corrections naming no outcome on file: {review.orphans}")  # fmt: skip
    return lines


def _driver(d: DriverSummary) -> list[str]:
    outcomes = ", ".join(f"{code} {n}" for code, n in d.outcomes.items()) or "none"
    parts = ", ".join(f"{k} {v:,.0f}" for k, v in d.attribution.items())
    primary = ", ".join(f"{cause_words(Cause(c), False)} {n}" for c, n in d.primary.items()) or "none"
    return [
        f"{d.driver_id}: decisions {sum(d.outcomes.values())} ({outcomes});"
        f" closed trades {d.trades}, tickets {d.tickets}; {_three(d.three_counts)}",
        f"  account trades: net Rs {d.net_rs:,.0f}, max drawdown Rs {d.max_drawdown_rs:,.0f}, worst day"
        f" {_rs(d.worst_day_rs)}, worst trade {_rs(d.worst_trade_rs)} (tickets never summed in)",
        f"  attribution (Rs): {parts}; poor fit {d.poor_fit}",
        f"  primary causes: {primary}; unclassified {d.unclassified}; not testable {sum(d.not_testable.values())}",
    ]


def _row(r) -> str:
    return ROW.format(
        control=r.control_id,
        measure=r.measure,
        status=r.status,
        sessions=r.sessions,
        road_slots=r.road_slots,
        mean=_num(r.mean),
        bound=_num(r.bound),
        batch=r.batch,
        da=r.driver_abstentions,
        ca=r.control_abstentions,
        un=r.unavailable,
        cut=r.after_cut,
        note=r.note,
    )


def _three(counts) -> str:
    if counts is None:
        return "three counts not supplied"
    return "eligible {}, fillable {}, executed {}".format(*counts)


def _num(value) -> str:
    return "none" if value is None else f"{value:+.3f}"


def _rs(value) -> str:
    return "none" if value is None else f"Rs {value:,.0f}"


def _days(days) -> str:
    return ", ".join(str(d) for d in days) or "none"
