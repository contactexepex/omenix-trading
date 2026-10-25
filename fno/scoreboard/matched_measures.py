"""Story S6's share on scoreboard A (S3 criterion 5): the measures (rupees only: no brake applies to a shadow account)
and the do-nothing view (a) on each book's standardised series, with each closed take's one-lot capital tied held from
its entry session to its exit. There is no view (b): scoreboard A has no account. S6's functions, no second copy."""

from __future__ import annotations

from collections.abc import Sequence

from .do_nothing import DoNothing
from .entry_facts import one_lot_capital
from .matched import DayScore, Results, series_of
from .matched_actions import TAKE
from .matched_days import BookDay
from .standard_unit import CLOSED, OPEN
from .trade_measures import BY_DECISION_DAY, drawdown, trade_measures

# The standard unit carries no operating or AI cost (S1: no account, one lot), so A's verdict stands for every book,
# while scoreboard B withholds an AI book's verdict until F8 knows its cost.
NO_OPERATING_COST = 0.0
# Judge 196 note 1: a take's net sits on its decision day, its capital only on the series' days, so a take exiting after
# the last series day loses capital-days and flatters view (a). It is descriptive (RM1's gate reads scoreboard B).
CAPITAL_CUT = "capital-days after the series' last day are left out for {n} take(s), so view (a) flatters the book"
NOT_COMPARABLE = "not comparable: {cut}; RM1 reads scoreboard B's full capital path"


def _takes(days: Sequence[BookDay], results: Results, scored: set) -> list:
    return [(d, o, a, results[(d.book, d.day, o)]) for d in days if d.day in scored
            for o, a in d.actions.items() if a.kind == TAKE and (d.book, d.day, o) in results]  # fmt: skip


def a_measures(
    days: Sequence[BookDay], results: Results, scores: Sequence[DayScore], against: DoNothing | None
) -> dict:
    series, scored = series_of(scores), {s.day for s in scores}
    takes = [t for t in _takes(days, results, scored) if t[3].status == CLOSED]
    opened = sum(r.status == OPEN for d in days for o, a in d.actions.items()
                 if (r := results.get((d.book, d.day, o))) is not None)  # fmt: skip
    out = {"measures": {**trade_measures([t[3].net for t in takes], opened), **drawdown(series, None, BY_DECISION_DAY)}}
    if against is not None:
        capital, unrecorded = capital_path(takes, series.days)
        compared = against.compare(series, capital, NO_OPERATING_COST, unrecorded)
        out["do_nothing"] = {key: value for key, value in compared.items() if key != "view_b"}
        cut = sum(t[3].exited_on > series.days[-1] for t in takes) if series.days else 0
        out["do_nothing"]["capital_cut"] = CAPITAL_CUT.format(n=cut) if cut else ""
        if cut:  # review 120 (response 200 disclosure 8): the figures stay, the comparison is withheld
            view = out["do_nothing"]["view_a"]
            view.update(beats_index_after_tax=None, beats_cash_after_tax=None,
                        reason=NOT_COMPARABLE.format(cut=CAPITAL_CUT.format(n=cut)))  # fmt: skip
    return out


def capital_path(takes: list, days: Sequence) -> tuple[list[float], list[str]]:
    """Each session's one-lot capital tied by the closed takes held at its close (entry session to exit), and the takes
    whose record holds no capital (the comparison is then not computable)."""
    capital, unrecorded = [0.0] * len(days), []
    for book_day, opportunity_id, action, result in takes:
        one_lot = one_lot_capital(action.record)
        if one_lot is None:
            unrecorded.append(f"{book_day.day.isoformat()}/{opportunity_id}")
            continue
        for i, day in enumerate(days):
            if book_day.day <= day < result.exited_on:
                capital[i] += one_lot
    return capital, unrecorded
