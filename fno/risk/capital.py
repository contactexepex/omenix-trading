"""The cap on the stressed SPAN figure of the one- and two-leg structures (story STR1b, review 100 point 2).

The owner's factor k stresses the scanning risk, `max(0, k x scan - NOV)` per lot, and the exposure (story C2c). For a
bought option or a debit spread that adds k - 1 times the premium already paid (judge 106: Rs 15,828.64 on the real ATM
call), money it cannot lose a second time. So for the six STR1 codes the stressed SPAN figure is capped at the worst
terminal loss beyond the premium paid, though never below the broker's own unstressed figure `max(0, scan - NOV)` (C2 is
never looser than the broker at entry, judge 77 addendum 3). The cap, from the margin row, is 0 when the row's net
option value is a debit (LC, LP, CDS, PDS), and `width x lot size - credit` for a credit spread (CCS, PCS). The exposure
is outside the cap: it is charged on the short legs' notional, not bounded by the spread's loss. SF, SC and BF are not
capped: the owner's 1.45 came from a BF case (response 77), so changing it is the owner's call."""

from __future__ import annotations

from ..constants import STRUCTURES_ONE_SIDE


def stress_cap_per_lot(structure: str, width: float, nov: float, lot_size: int) -> float | None:
    """Rupees per lot, or None when the structure is not capped. `nov`: the row's net option value per lot, bought legs
    plus (a credit spread's is minus its credit)."""
    if structure not in STRUCTURES_ONE_SIDE:
        return None
    return max(0.0, width * lot_size + nov) if nov < 0 else 0.0
