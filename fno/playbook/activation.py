"""The activation gate of the one- and two-leg structures (story STR1b, judge 115 should-fix 2): a version whose
structure is an STR1 code may not be used while a gate that blocks that use is open (`STR1_ACTIVATION_PENDING`). A
registered research candidate is used as a shadow; `paper` and `paused` are paper use. An unregistered research file is
not used, so it is never refused (a draft idea file must not stop the playbook from loading). D2 takes its shadows and
its approved versions only from the loaded playbook, so this one check in the loader and the status changer covers
D1 and D2."""

from __future__ import annotations

from ..constants import STR1_ACTIVATION_PENDING, STRUCTURES_ONE_SIDE, USE_PAPER, USE_SHADOW, PlaybookStatus
from .schema import Strategy

PAPER_STATUSES = frozenset({PlaybookStatus.PAPER, PlaybookStatus.PAUSED})
REFUSED = "{code} cannot be used for {use} while these activation gates are open: {gates} (story STR1b)"


def activation_problem(strategy: Strategy, registered: bool) -> str:
    """Why this version may not be used ("" when it may)."""
    code = strategy.structure.code
    use = USE_PAPER if strategy.status in PAPER_STATUSES else USE_SHADOW if registered else None
    if code not in STRUCTURES_ONE_SIDE or use is None:
        return ""
    gates = [gate for gate, uses in STR1_ACTIVATION_PENDING.items() if use in uses]
    return REFUSED.format(code=code, use=use, gates=", ".join(gates)) if gates else ""
