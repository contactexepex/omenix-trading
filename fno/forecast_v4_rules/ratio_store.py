"""The premium ratio, computed once per month and stored (story G7b completion, part b2; judge 578.1 n2): the ratio is
computed only on the refit day itself, from the inputs present then, and written write-once to Drive,
`v4/ratios/<measure>/<question>/<YYYY-MM>.json` (the ratio, the window's first and last day, its count, how many of
its points rest on A16b's back-fill, `backfill_window` (W8), and the inputs' SHA-256); every later day of that month
reads it and never recomputes it. The capture stores it on the refit day whatever the release (judge 598 SF1). A
refit day with no capture run leaves the month not eligible, counted; never a late ratio (it could read files archived
after the refit day; judge 598, item 3). A refit with no eligible window
is stored too (`null`): the month stays not eligible, a transient gap included."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import date

from .implied import PremiumRatio

RATIOS_FOLDER = "v4/ratios"


def ratio_path(measure: str, question: str, refit_day: date) -> str:
    return f"{RATIOS_FOLDER}/{measure}/{question}/{refit_day:%Y-%m}.json"


class StoredRatio:
    def __init__(self, ratio: PremiumRatio, question: str, measure: str, today: date,
                 get: Callable[[str], bytes | None], put: Callable[[str, bytes], None],
                 backfilled: frozenset[date] = frozenset()):  # fmt: skip
        """`today`: the capture's day; `get(path)`: the verified stored bytes or None; `put`: a write-once save;
        `backfilled`: the window points resting on A16b's back-fill (W8; none for the close proxy)."""
        self.ratio, self.question, self.measure, self.today = ratio, question, measure, today
        self.get, self.put, self.backfilled, self.known = get, put, backfilled, {}

    def at(self, refit_day: date) -> float | None:
        """The month's ratio, asked once per refit day and remembered for the run."""
        if refit_day not in self.known:
            self.known[refit_day] = self._stored_or_new(refit_day)
        return self.known[refit_day]

    def _stored_or_new(self, refit_day: date) -> float | None:
        path = ratio_path(self.measure, self.question, refit_day)
        stored = self.get(path)
        if stored is not None:
            return json.loads(stored)["ratio"]
        if self.today != refit_day:
            return None  # the refit day was missed: no late ratio
        window = self.ratio.window(refit_day) or []
        points = "".join(f"{t.isoformat()} {self.ratio.ratios[t]!r}\n" for t in window)
        document = {
            "question": self.question, "measure": self.measure, "refit_day": refit_day.isoformat(),
            "ratio": self.ratio.at(refit_day), "count": len(window),
            "backfill_window": len(self.backfilled & set(window)),
            "first": window[0].isoformat() if window else None, "last": window[-1].isoformat() if window else None,
            "inputs_sha256": hashlib.sha256(points.encode()).hexdigest(),
        }  # fmt: skip
        self.put(path, json.dumps(document, sort_keys=True).encode("utf-8"))
        return document["ratio"]
