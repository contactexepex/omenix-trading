"""What the A16h probe keeps of the feed: per instrument, how many ticks arrived and when, and the latency from the
tick's own exchange time (`tsInMillis`) to our receipt. Counts and times only; no tick value is kept."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

FEED_KEY, FEED_TYPE, EXCHANGE_TIME = "feed_key", "feed_type", "tsInMillis"
NO_EXCHANGE_TIME = "no exchange time in the ticks"


class TickCounter:
    def __init__(self, clock: Callable[[], datetime]):
        self.clock = clock
        self.ticks: Counter[tuple[str, str]] = Counter()  # (feed type, instrument key)
        self.last_seen: dict[tuple[str, str], datetime] = {}
        self.first_seen: dict[tuple[str, str], datetime] = {}
        self.classes: dict[str, str] = {}
        self.latencies: list[float] = []
        self._exchange_seen: dict[str, float] = {}

    def on_tick(self, meta: Mapping) -> None:
        """The feed's callback: it passes the topic's meta only."""
        key, now = (str(meta.get(FEED_TYPE)), str(meta.get(FEED_KEY))), self.clock()
        self.ticks[key] += 1
        self.first_seen.setdefault(key, now)
        self.last_seen[key] = now

    def sample(self, nested: Mapping, feed_type: str) -> None:
        """A `get_ltp()` answer (exchange -> segment -> key -> fields): each key's new exchange time against our last
        receipt of that key."""
        for token, fields in _leaves(nested):
            key = (feed_type, token)
            stamp = fields.get(EXCHANGE_TIME) if isinstance(fields, Mapping) else None
            if not stamp or stamp == self._exchange_seen.get(key) or key not in self.last_seen:
                continue
            self._exchange_seen[key] = stamp
            sent = datetime.fromtimestamp(float(stamp) / 1000, UTC)
            self.latencies.append((self.last_seen[key] - sent).total_seconds())

    def report(self, classes: Mapping[str, str]) -> list[str]:
        """One line per class and feed type: instruments, how many ticked, ticks and ticks a second; then latency."""
        members: dict[str, list[tuple[str, str]]] = defaultdict(list)
        types = sorted({feed_type for feed_type, _ in self.ticks}) or ["ltp"]
        for token, name in classes.items():
            for feed_type in types:
                members[f"{name} [{feed_type}]"].append((feed_type, token))
        lines = []
        for name in sorted(members):
            keys = members[name]
            ticked = [k for k in keys if self.ticks[k]]
            count = sum(self.ticks[k] for k in keys)
            lines.append(
                f"{name}: {len(ticked)} of {len(keys)} ticked, {count} ticks, {self._rate(keys, count)} a second"
            )
        return lines + [self._latency_line()]

    def _rate(self, keys: list[tuple[str, str]], count: int) -> str:
        seen = [k for k in keys if k in self.first_seen]
        if not seen:
            return "0"
        span = (max(self.last_seen[k] for k in seen) - min(self.first_seen[k] for k in seen)).total_seconds()
        return f"{count / span:.2f}" if span > 0 else "n/a"

    def _latency_line(self) -> str:
        if not self.latencies:
            return f"latency: {NO_EXCHANGE_TIME}"
        ordered = sorted(self.latencies)
        p95 = ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]
        median = ordered[len(ordered) // 2]
        return f"latency (receipt minus exchange time): median {median:.3f} s, 95th {p95:.3f} s, n {len(ordered)}"


def _leaves(nested: Mapping):
    for by_segment in (nested or {}).values():
        for by_key in (by_segment or {}).values():
            yield from ((str(k), v) for k, v in (by_key or {}).items())
