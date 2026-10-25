"""The checks on the day's market data (story C3): every spot in the pack is within `limit` of the previous session's
official close unless the day is flagged as a shock, and the previous session's NSE F&O file is archived (session per
the A7 calendar). Both stop new trades only (judge 81): freshness is proven by the window and record checks, so on a
big-move day (a crash, a budget) due exits still fill at valid quotes, as design 9 requires.

An A4 snapshot holds one spot per monthly chain (the pack's `spot:<expiry>` items, story E2b) (MONTHLY_EXPIRIES = 2),
each from its own provider call seconds apart, so the spots differ slightly. They must agree within `SPOT_AGREEMENT`; a
larger gap means one chain carries a wrong underlying price (a future's basis is about 0.3-1% a month out)."""

from __future__ import annotations

from collections.abc import Sequence

from ..research_data.calendar import SessionCalendar
from ..storage.raw_source import NseArchiveSource
from ..storage.raw_store import RawFileStore
from .data_checks import CheckSubject, DataCheck
from .shock import ShockFlags

SPOT_LIMIT = 0.02  # story C3: spot within 2% of the previous close
SPOT_AGREEMENT = 0.002  # 0.2% (~50 points): two index readings seconds apart; reasoning only, until real captures
ROUNDING = 1e-9  # float rounding of the ratio: exactly 2% passes
SPOT_PREFIX, CLOSE_PREFIX = "spot:", "close:"  # one `spot:<expiry>` item per monthly chain (E2b)


def pack_items(subject: CheckSubject, prefix: str) -> dict[str, object]:
    return {i["name"]: i["value"] for i in subject.pack.body["items"] if i["name"].startswith(prefix)}


class SpotNearPreviousClose(DataCheck):
    name, prices_unverified = "spot", False

    def __init__(self, calendar: SessionCalendar, shocks: ShockFlags, limit: float = SPOT_LIMIT,
                 agreement: float = SPOT_AGREEMENT):  # fmt: skip
        self.calendar, self.shocks, self.limit, self.agreement = calendar, shocks, limit, agreement

    def problems(self, subject: CheckSubject) -> list[str]:
        chains = pack_items(subject, SPOT_PREFIX)
        refused = [r["name"] for r in subject.pack.body.get("refused", []) if r["name"].startswith(SPOT_PREFIX)]
        blank = sorted(name.removeprefix(SPOT_PREFIX) for name in refused + [n for n, v in chains.items() if not v])
        if blank:
            return [f"the pack holds no spot for the chain(s) {', '.join(blank)}: one spot per recorded chain"]
        spots = sorted(set(chains.values()))
        previous = self.calendar.previous_session(subject.day)
        close = pack_items(subject, CLOSE_PREFIX).get(f"{CLOSE_PREFIX}{previous.isoformat()}")
        if not spots:
            return ["the pack holds no spot"]
        if spots[-1] / spots[0] - 1 > self.agreement + ROUNDING:
            return [f"the pack's spots {spots[0]:,.2f} and {spots[-1]:,.2f} disagree by more than {self.agreement:.1%}"]
        if not close or not close.get("nifty"):
            return [f"the pack holds no official close of the previous session {previous}"]
        previous_close = close["nifty"]
        moves = [spot / previous_close - 1 for spot in spots]
        if all(abs(m) <= self.limit + ROUNDING for m in moves) or self.shocks.flagged(subject.day):
            return []
        move = max(moves, key=abs)
        return [
            f"spot {previous_close * (1 + move):,.2f} is {move:+.2%} from the previous close {previous_close:,.2f} "
            f"({previous}), beyond {self.limit:.0%}, and the day is not flagged as a shock ({self.shocks.source})"
        ]


class PreviousSessionFile(DataCheck):
    name, prices_unverified = "previous NSE file", False

    def __init__(self, stores: Sequence[RawFileStore], source: type[NseArchiveSource], calendar: SessionCalendar):
        self.stores, self.source, self.calendar = tuple(stores), source, calendar

    def problems(self, subject: CheckSubject) -> list[str]:
        previous = self.calendar.previous_session(subject.day)
        path = self.source.path_for(previous)
        if any(store.get(path) is not None for store in self.stores):
            return []
        return [f"NSE's file of the previous session {previous} is not archived ({path})"]
