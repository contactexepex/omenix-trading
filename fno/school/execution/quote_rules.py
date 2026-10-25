"""How a slot quote's displayed size reaches E4 (orchestrator, 22 Oct 2026, design A; story 7.2, "the size gate is
waived in practice"). A measured size is passed as recorded. A quote whose size was never measured
(`SlotQuote.sizes_measured` False: the simulator's history) has no size limit under practice rules and no size at all
under live rules, where the gate names it `size_not_measured`. Only the practice roots (`practice_wiring.py`) build
practice rules; every live path uses `LIVE` (tests pin it)."""

import math
from dataclasses import dataclass

from ..contracts.snapshot import SlotQuote

PRACTICE_SIZE_NOTE = "size gate not tested in practice"


@dataclass(frozen=True, kw_only=True)
class QuoteRules:
    practice: bool  # keyword-only: a practice root names it, so the isolation test can find every one

    def sizes(self, quote: SlotQuote) -> tuple[float | None, float | None]:
        """(bid size, ask size) as E4 reads them."""
        if quote.sizes_measured:
            return quote.bid_qty, quote.ask_qty
        return (math.inf, math.inf) if self.practice else (None, None)

    def size_not_measured(self, quote: SlotQuote) -> bool:
        """Refused live for its size alone: valid and priced on both sides, with no displayed size measured. A quote
        missing a price stays one-sided under any rules."""
        return not self.practice and not quote.sizes_measured and quote.two_sided


LIVE = QuoteRules(practice=False)
