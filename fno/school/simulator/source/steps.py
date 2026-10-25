"""A road's strike step from the archived rows (story MS-SIM-c): the most common gap between listed strikes near the
money. The catalogue contract wants one step per expiry; history states none, so it is read off the listing."""

from collections import Counter
from collections.abc import Iterable

NEAR_THE_MONEY = 0.05  # of the index close


def strike_step(strikes: Iterable[float], index_close: float) -> float | None:
    """None when there are fewer than two strikes to compare. Strikes within 5% of the close are compared first, since
    far strikes are often listed more sparsely; all strikes only if the near ones give no gap."""
    ordered = sorted(set(strikes))
    near = [s for s in ordered if abs(s - index_close) <= NEAR_THE_MONEY * index_close]
    for group in (near, ordered):
        gaps = Counter(round(b - a, 6) for a, b in zip(group, group[1:], strict=False))
        if gaps:
            return max(gaps.items(), key=lambda item: (item[1], -item[0]))[0]
    return None
