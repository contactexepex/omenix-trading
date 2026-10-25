"""What `fno factory status` and `report` print (story R1): each idea's place in the trial count and its last gate."""

from __future__ import annotations

from .card import IdeaCard
from .constants import BACKFILLED
from .gate_log import GateRow
from .trial_count import FalsePasses, TrialCount


def idea_line(card: IdeaCard, count: TrialCount, last: GateRow | None) -> str:
    label = " (measurement)" if card.measurement else ""  # "never promoted" is a shadow's label (R1c)
    head = f"{card.idea_id} v{card.version}{label}: {count.label(card.trial_id)}"
    if last is None:
        return f"{head}; no gate-log row (register or back-fill it)"
    backfilled = " (back-filled)" if BACKFILLED in last.numbers.split(";") else ""
    return f"{head}; last gate {last.gate} {last.outcome} on {last.on}{backfilled}"


def false_pass_line(count: TrialCount, passes: FalsePasses) -> str:
    left_out = f"; measurement trials left out: {', '.join(passes.measurements)}" if passes.measurements else ""
    return (
        f"{count.total} trials in the ledger; expected false passes at {passes.alpha:g} one-sided: "
        f"{passes.expected:.2f} ({passes.tests} trials{left_out})"
    )
