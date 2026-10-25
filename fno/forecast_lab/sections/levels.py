"""The evening's levels and flows table (story FL1-1d-2), from NSE's evening files of the day only (the as-of rule:
an older value is never shown as the day's):
- for NIFTY and BANKNIFTY, from the day's F&O bhavcopy, the nearest expiry's put-call ratio (put OI over call OI, also
  for the previous session), the strikes with the most call and put open interest (the "walls") and max pain, by
  `fno/analytics.py`'s own functions;
- for NIFTY, FII and DII net cash (P8's archive) and FIIs' net index-futures contracts (A8's participant OI file).
A value whose file is not out yet is "not out yet", in words. The morning shows no levels table (the designer's
page)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime

from ...analytics import max_pain, put_call_ratio
from ...constants import NIFTY_SYMBOL, OI_FUTURE_INDEX, PARTICIPANT_FII
from ...fo_bhavcopy import BadFile, read_fo_file
from ...models import IST, OptionChain, OptionQuote
from ...research_data.nifty_panel import DailyFiles
from ...research_data.participant_oi import read_participant_oi
from ..page.cues import Cue

OPTION = "IDO"
NOT_OUT, NONE_IN_FILE = "not out yet", "none in the file"
NAMES = ("PCR", "PCR (previous session)", "Call wall", "Put wall", "Max pain")
FLOWS = ("FII cash (Rs crore)", "DII cash (Rs crore)")
FII_FUTURES = "FII index futures (net contracts)"


def nearest_chain(underlying: str, day: date, rows: list[dict]) -> OptionChain | None:
    """The nearest expiry's options of the underlying, with their open interest (the bhavcopy has no bid or ask)."""
    options = [r for r in rows if r["TckrSymb"] == underlying and r["FinInstrmTp"] == OPTION
               and r["OptnTp"] in ("CE", "PE") and date.fromisoformat(r["XpryDt"][:10]) >= day]  # fmt: skip
    if not options:
        return None
    expiry = min(date.fromisoformat(r["XpryDt"][:10]) for r in options)
    chain = OptionChain(underlying, 0.0, expiry, datetime.combine(day, datetime.min.time(), IST), 0)
    for r in options:
        if date.fromisoformat(r["XpryDt"][:10]) == expiry:
            strike = float(r["StrkPric"])
            chain.quotes[(strike, r["OptnTp"])] = OptionQuote(strike, r["OptnTp"], 0.0, oi=float(r["OpnIntrst"] or 0))
    return chain


def _wall(chain: OptionChain, kind: str) -> float | None:
    side = [q for (_, k), q in chain.quotes.items() if k == kind]
    return max(side, key=lambda q: q.oi).strike if side else None


def _cue(name: str, value: float | None, day: date) -> Cue:
    """A value with its day, or "none in the file" when the file has no such side (never a made-up zero)."""
    return Cue(name, value, as_of=day) if value is not None else Cue(name, as_of=day, text=NONE_IN_FILE)


def _pcr(chain: OptionChain | None) -> float | None:
    ratio = put_call_ratio(chain) if chain is not None else None
    return round(ratio, 2) if ratio is not None else None


class Levels:
    def __init__(self, fo_files: Sequence[DailyFiles], participant: DailyFiles, flows: Callable[[date], Mapping],
                 previous: Callable[[date], date]):  # fmt: skip
        """`flows(day)`: session -> (FII net, DII net) in Rs crore, up to `day` (P8's archive)."""
        self.fo_files, self.participant, self.flows, self.previous = tuple(fo_files), participant, flows, previous

    def _chain(self, underlying: str, day: date) -> OptionChain | None:
        for files in self.fo_files:
            if not files.covers(day):
                continue
            name, data = files.get(day)
            if data is None:
                continue
            try:
                return nearest_chain(underlying, day, read_fo_file(name, data))
            except BadFile:
                continue
        return None

    def levels(self, underlying: str, day: date) -> tuple[Cue, ...]:
        today, before = self._chain(underlying, day), self._chain(underlying, self.previous(day))
        if today is None:
            out = [Cue(n, text=NOT_OUT) for n in NAMES]
        else:
            previous = self.previous(day)
            last = _cue(NAMES[1], _pcr(before), previous) if before else Cue(NAMES[1], text=NOT_OUT)
            out = [_cue(NAMES[0], _pcr(today), day), last, _cue(NAMES[2], _wall(today, "CE"), day),
                   _cue(NAMES[3], _wall(today, "PE"), day), _cue(NAMES[4], max_pain(today), day)]  # fmt: skip
        return tuple(out + (self._nifty_flows(day) if underlying == NIFTY_SYMBOL else []))

    def _nifty_flows(self, day: date) -> list[Cue]:
        nets = self.flows(day).get(day)
        cash = [Cue(n, v, as_of=day) for n, v in zip(FLOWS, nets, strict=True)] if nets else [
            Cue(n, text=NOT_OUT) for n in FLOWS]  # fmt: skip
        name, data = self.participant.get(day)
        if data is None:
            return [*cash, Cue(FII_FUTURES, text=NOT_OUT)]
        net = read_participant_oi(data, name, day).position(PARTICIPANT_FII, OI_FUTURE_INDEX).net
        return [*cash, Cue(FII_FUTURES, float(net), as_of=day)]
