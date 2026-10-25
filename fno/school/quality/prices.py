"""Impossible prices in a chain (story 3.5): EDGE1's rule (protocol section 7, revision 7) read off a chain of two-sided
quotes. A sold leg and the bought leg of its type form a vertical that is worth between 0 and its width; every pair of
strikes of one expiry and type is judged (neighbours are not enough once a leg is a range: a wide quote between two
tight ones can hide a broken wider vertical).

EDGE1 judged last-trade closes, one price a leg. A quote is a range, so a vertical is impossible only when no price
inside both legs' bid-ask ranges can satisfy the bounds. Judged on mids instead, 8-61 legs a road-day (neighbour pairs)
and 9-87 (all pairs) of the whole chain broke the rule through spread noise alone on the recorded 21 and 22 October
chains, and inside the band MIDCPNIFTY's 15 and 6; judged on ranges, none did. Both legs of a broken vertical are
flagged, since the chain cannot say which of the two is stale. Single legs get the bounds no market can break: a call's
bid is not above the index, a put's bid not above its strike. Those are loose (they seldom bind); the vertical rule is
the one with teeth. Prices are compared to a tick's fraction (1e-9) so float noise never flags a legal vertical."""

from collections import defaultdict
from collections.abc import Collection
from itertools import combinations

from ..constants import OptionKind
from ..contracts.snapshot import ContractKey, SlotQuote, SlotSnapshot

TOLERANCE = 1e-9


def impossible_keys(snapshot: SlotSnapshot, among: Collection[ContractKey] | None = None) -> frozenset[ContractKey]:
    """Every two-sided leg that breaks a bound or sits in a vertical that does, judged among `among` (default: the
    whole chain). A road is judged on its band only, so a stale far wing cannot flag the legs near the money."""
    by_chain: dict[tuple, list[tuple[float, SlotQuote]]] = defaultdict(list)
    flagged: set[ContractKey] = set()
    for key, quote in snapshot.quotes.items():
        if not quote.two_sided or (among is not None and key not in among):
            continue
        by_chain[key.expiry, key.kind].append((key.strike, quote))
        if quote.bid > (snapshot.spot if key.kind is OptionKind.CALL else key.strike) + TOLERANCE:
            flagged.add(key)
    for (expiry, kind), legs in by_chain.items():
        legs.sort(key=lambda leg: leg[0])
        for (low, low_quote), (high, high_quote) in combinations(legs, 2):
            dearer, cheaper = (low_quote, high_quote) if kind is OptionKind.CALL else (high_quote, low_quote)
            if dearer.ask - cheaper.bid < -TOLERANCE or dearer.bid - cheaper.ask > high - low + TOLERANCE:
                flagged |= {ContractKey(expiry, low, kind), ContractKey(expiry, high, kind)}
    return frozenset(flagged)
