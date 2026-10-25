"""The message's text (stories FL1-1c, FL1-1d and FL1-1f): the edition's title with what "right" means, then per
index the morning's one line, or the evening's top block (`verdict_words.py`: the verdict or why there is none, why,
the record) and its next forecasts; then the morning's confirmations and the status line."""

from __future__ import annotations

from .cues import FAILED, NOT_OUT_YET
from .model import IndexView, PageView
from .plain import EDITIONS, RIGHT, day_short, forecast_words, index_line, status_line
from .verdict_words import top_block


def _evening(index: IndexView, view: PageView) -> list[str]:
    ahead = forecast_words(index)
    unavailable = tuple(s.why for s in view.cues if s.status in (NOT_OUT_YET, FAILED) and s.why)
    block = top_block(index, view.day, view.next_session, unavailable)
    return [*block, *([f"Next: {' · '.join(ahead)}"] if ahead else [])]


def slack_lines(view: PageView) -> list[str]:
    title, at = EDITIONS[view.edition]
    if view.edition == "evening":
        lines = [line for index in view.indices for line in _evening(index, view)]
    else:
        lines = [index_line(index, view.day, view.next_session) for index in view.indices]
    return [f"*{title}* ({day_short(view.day)}, {at}) {RIGHT}", *lines, *view.confirmation, status_line(view)]
