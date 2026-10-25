"""A later expiry too thin to value is a note, not a failure (orchestrator and owner's rule, 22 Oct 2026).

On the first live day FINNIFTY's next monthly had no strike with both a two-sided call and put at 15:04, so it had
no parity forward; the record named it, and the step failed, as it would most days. An expiry beyond the nearest
eligible one, with no quotes used or no parity forward, is now a recorded "no forecast for that expiry": it stays in
the record's problems, the step names it in a `note:` line, and it does not fail the step. The same gap on the
nearest eligible expiry (or with no usable expiry at all) is still a failure."""

from __future__ import annotations

from .constants import NOT_ELIGIBLE, OK
from .valuation import NO_FORWARD, NO_QUOTES

THIN_REASONS = (NO_FORWARD, NO_QUOTES)


def thin_problems(record: dict) -> set[str]:
    """The record's problems that are later expiries too thin to value, while the nearest eligible one is usable."""
    expiries = sorted(((e["expiry"], e) for e in (record.get("valuation") or {}).get("expiries", [])
                       if e["status"] != NOT_ELIGIBLE), key=lambda pair: pair[0])  # fmt: skip
    if not expiries or expiries[0][1]["status"] != OK:
        return set()
    return {f"{day}: {e['reason']}" for day, e in expiries[1:] if e["reason"] in THIN_REASONS}
