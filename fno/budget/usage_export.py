"""Reading one AI session's usage (story F8). Python cannot call Claude's session tools, so a Claude session saves them
into one JSON file outside the repository: `{"captured_at": <ISO time with zone>, "session": <get_session>,
"result_pages": [{"before_id": <cursor used, null for the first call>, "response": <list_events(kinds=["result"])>},
...]}`, newest page first, back to the oldest. `SessionUsageReader` is the interface; `ExportFileUsageReader` reads such
a file. The pages must chain (each cursor is the newer page's `first_id`; every page but the last has `has_more` true;
the last page omits it, as read on 15 Oct 2026, or says false), so a dropped page is refused. Only numbers are taken,
never message text: per IST day, the wall minutes of that day's turns (`duration_ms`) and their main-loop tokens
(`usage`), blank when any turn of the day lacks them. Days on or after the capture's IST date are not complete in the
export, so they are never recorded from it."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from .usage_reader import DayUsage, ExportRefused, SessionUsageReader, ist_time, shaped

TOKEN_FIELDS = {  # ledger column -> field of a result event's `usage`
    "input_tokens": "input_tokens",
    "output_tokens": "output_tokens",
    "cache_read_tokens": "cache_read_input_tokens",
    "cache_write_tokens": "cache_creation_input_tokens",
}
SOURCE = "get_session + list_events(result) export"
INCOMPLETE = "the export's last page has has_more true: older result events are missing, so nothing is recorded"
BROKEN_CHAIN = "page {n} was not read with the previous page's first_id: a page is missing, so nothing is recorded"
MORE_AFTER_END = "page {n} follows a page without has_more true: the pages are out of order"
NO_SESSION_ID = "the export's session record has no id"
NO_RESULTS = "the export holds no result events: nothing to record (a changed export shape is refused, not skipped)"


class ExportFileUsageReader(SessionUsageReader):
    def __init__(self, path: Path):
        self._export = shaped(json.loads(path.read_text(encoding="utf-8")), dict, "the export")

    def complete_before(self, today: date) -> date:
        """A day still running when the export was taken is not complete in it."""
        return min(today, ist_time(self._captured_at(), "captured_at").date())

    def _captured_at(self) -> str:
        return self._export.get("captured_at") or ""

    def days(self) -> list[DayUsage]:
        session = _unwrap(shaped(self._export.get("session") or {}, dict, "the session record"))
        session_id = session.get("id") or ""
        if not session_id:
            raise ExportRefused(NO_SESSION_ID)
        model = session.get("configured_model") or (session.get("session_context") or {}).get("model") or ""
        by_day = defaultdict(list)
        for result in _results(shaped(self._export.get("result_pages") or [], list, "result_pages")):
            by_day[ist_time(result["created_at"], "created_at").date()].append(result["result"])
        return [_day_usage(day, session_id, model, by_day[day]) for day in sorted(by_day)]


def _unwrap(part: dict) -> dict:
    return part.get("ccr", part)


def _chained(pages: list) -> list[dict]:
    """The responses, once each page is shown to be read with the newer page's first_id and the last is the end."""
    responses, cursor = [], None
    for n, page in enumerate(pages, start=1):
        response = _unwrap(shaped(shaped(page, dict, f"page {n}").get("response") or {}, dict, f"page {n}'s response"))
        if response.get("has_more", False) not in (True, False):
            raise ExportRefused(f"page {n}: has_more is {response['has_more']!r}, not true, false or absent")
        if page.get("before_id") != cursor:
            raise ExportRefused(BROKEN_CHAIN.format(n=n))
        if responses and responses[-1].get("has_more") is not True:
            raise ExportRefused(MORE_AFTER_END.format(n=n))
        responses.append(response)
        cursor = response.get("first_id")
    if not responses or responses[-1].get("has_more") is True:  # the real last page omits has_more (15 Oct)
        raise ExportRefused(INCOMPLETE)
    return responses


def _results(pages: list) -> list[dict]:
    seen, results = set(), []
    for page in _chained(pages):
        for event in shaped(page.get("data") or [], list, "a page's data"):
            result = shaped(shaped(event, dict, "an event").get("result"), dict, "an event's result")
            if not isinstance(event.get("created_at"), str):
                raise ExportRefused("a result event has no created_at")
            uuid = result.get("uuid")
            if not uuid:
                raise ExportRefused(f"a result event of {event.get('created_at')} has no uuid")
            if uuid not in seen:
                seen.add(uuid)
                results.append({"created_at": event["created_at"], "result": _figures(result)})
    if not results:
        raise ExportRefused(NO_RESULTS)
    return results


def _figures(result: dict) -> dict:
    """The few numbers of a result event; its text (the reply) is dropped here."""
    figures = result.get("internal_anthropic_catchall", result)
    return {"duration_ms": figures.get("duration_ms"), "usage": figures.get("usage")}


def _day_usage(day: date, session_id: str, model: str, turns: list[dict]) -> DayUsage:
    if not all(_is_duration(turn["duration_ms"]) for turn in turns):
        raise ExportRefused(f"{day}: a result event has no valid duration_ms (a number of 0 or more)")
    minutes = round(sum(turn["duration_ms"] for turn in turns) / 60000, 2)
    return DayUsage(day, session_id, model, minutes, len(turns), _tokens(turns), SOURCE)


def _is_duration(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and value >= 0


def _tokens(turns: list[dict]) -> dict[str, int] | None:
    usages = [turn["usage"] for turn in turns]
    if any(not isinstance(u, dict) or any(not _is_count(u.get(f)) for f in TOKEN_FIELDS.values()) for u in usages):
        return None
    return {column: sum(u[field] for u in usages) for column, field in TOKEN_FIELDS.items()}


def _is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
