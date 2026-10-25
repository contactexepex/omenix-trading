"""The allowed status changes (story D1 criterion 3) and who may make each. A version with no registry row is an
unregistered candidate (`research`); its first row either registers it as a candidate or approves it."""

from __future__ import annotations

from ..constants import APPROVER_DESK, APPROVER_HARD_LOSS_RULE, APPROVER_OWNER, PlaybookStatus
from .fields import PlaybookError

RESEARCH, PAPER, PAUSED, RETIRED = (
    PlaybookStatus.RESEARCH, PlaybookStatus.PAPER, PlaybookStatus.PAUSED, PlaybookStatus.RETIRED,
)  # fmt: skip
OWNER_ONLY = frozenset({APPROVER_OWNER})
ALLOWED = {
    # register a candidate: freezes its rule before a test and approves nothing, so the desk may do it too
    (None, RESEARCH): frozenset({APPROVER_OWNER, APPROVER_DESK}),
    (None, PAPER): OWNER_ONLY,  # research -> paper for a candidate registered at its approval
    (RESEARCH, PAPER): OWNER_ONLY,  # needs the evidence and the live-feature gate too (loader checks)
    (PAPER, PAUSED): frozenset({APPROVER_OWNER, APPROVER_HARD_LOSS_RULE}),
    (PAUSED, PAPER): OWNER_ONLY,
    **{(before, RETIRED): OWNER_ONLY for before in (None, RESEARCH, PAPER, PAUSED)},
}


def check_transition(before: PlaybookStatus | None, after: PlaybookStatus, approved_by: str) -> None:
    """PlaybookError unless `before -> after` is allowed and `approved_by` may make it."""
    allowed = ALLOWED.get((before, after))
    shown = before or "unregistered"
    if allowed is None:
        raise PlaybookError("status", f"{shown} -> {after} is not an allowed change")
    if approved_by not in allowed:
        raise PlaybookError("approved_by", f"{shown} -> {after} needs {sorted(allowed)}, not {approved_by!r}")
