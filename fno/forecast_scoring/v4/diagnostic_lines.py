"""The v4 report's descriptive lines (story G7b completion, part e). Descriptive only: nothing here feeds a ratio, a
baseline or a verdict.

- the pack's IV30 against the same day's end-of-day proxy (protocol 3.1's forward diagnostic) and A16b's back-filled
  candle-close `RV_s` against A16's live `RV_s` (W8's drift line, as its approved text says): the median of the paired
  daily ratios over every day and the latest 20, and their difference (`diagnostics.proxy_drift`, called);
- A16's live intraday `RV_s` against the close proxy (the gap yardstick B carries, W3): the ratio of the sums over
  every paired day and over the latest 20. A day's close proxy is one squared return, so its median is far below its
  mean and a median of daily ratios overstates the level gap (on 19-22 Oct 2026: median 4.09, ratio of sums 2.34).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from ...forecast_v4.diagnostics import proxy_drift

LINE = "{label}: {pairs} paired day(s); {kind} {all}, latest 20 {recent}, drift {drift} (descriptive only)"
IV30_LABEL = "pack IV30 / end-of-day IV30 proxy"
W8_LABEL = "back-filled candle RV_s / live A16 RV_s (W8)"
LEVEL_LABEL = "live intraday RV_s / close-proxy RV_s (W3's yardstick B)"
RECENT = 20
Pairs = Sequence[tuple[date, float | None, float | None]]


def _text(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def median_line(label: str, pairs: Pairs) -> str:
    drift = proxy_drift(pairs)
    return LINE.format(label=label, pairs=drift.pairs, kind="median ratio", all=_text(drift.median_ratio),
                       recent=_text(drift.recent_median_ratio), drift=_text(drift.drift))  # fmt: skip


def level_line(pairs: Pairs) -> str:
    paired = sorted((day, a, b) for day, a, b in pairs if a is not None and b is not None)  # a 0 proxy adds 0
    overall, recent = _sum_ratio(paired), _sum_ratio(paired[-RECENT:])
    drift = None if overall is None or recent is None else recent - overall
    return LINE.format(label=LEVEL_LABEL, pairs=len(paired), kind="ratio of sums", all=_text(overall),
                       recent=_text(recent), drift=_text(drift))  # fmt: skip


def _sum_ratio(paired) -> float | None:
    below = sum(b for _, _, b in paired)
    return sum(a for _, a, _ in paired) / below if below else None


def diagnostic_lines(iv30: Pairs, backfill: Pairs, level: Pairs) -> list[str]:
    return [median_line(IV30_LABEL, iv30), median_line(W8_LABEL, backfill), level_line(level)]
