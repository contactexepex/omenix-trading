"""E6's two shadow alerts worded for a measurement version (story R3, review 129, judge 226): its losses are the
expected cost of measuring, so the alerts say so and never read as a strategy failing; a second single-trade loss at
or beyond the cap is escalated as a possible simulator defect. Other versions keep E6's own wording."""

from __future__ import annotations

SINGLE_LOSS = (
    "F&O paper desk: {version} (measurement) shadow test, not paused: realised loss of Rs {cap:,.0f} or more "
    "({reason}); owner review or retirement required; no further promotion. It stays eligible for further "
    "hypothetical entries until the owner acts"
)
REPEATED = (
    "; loss {count} at or beyond the cap: possible simulator defect (fill or settlement path), check it before any "
    "strategy relies on that path"
)
CUMULATIVE = (
    "F&O paper desk: {version} (measurement) shadow test, not paused: {reason}; expected for a measurement (no edge), "
    "not a defect; the owner decides"
)


def single_loss_text(version: str, cap: float, reason: str, count: int) -> str:
    """`count`: this loss's place among the version's closed trades at or beyond the cap (1 for the first)."""
    return SINGLE_LOSS.format(version=version, cap=cap, reason=reason) + (
        REPEATED.format(count=count) if count > 1 else ""
    )


def cumulative_text(version: str, reason: str) -> str:
    return CUMULATIVE.format(version=version, reason=reason)
