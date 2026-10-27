"""What one `news resolve` run did: counts and fixed codes only, never a title, a link, a key or a host."""

from __future__ import annotations

from collections import Counter

from fno.ingestion.news import codes

COUNT_ORDER = ("examined", "already", "not_wrapper", "pending", "backlog", "expiring", "unexamined")


class ResolveReport:
    def __init__(self, apply: bool) -> None:
        self.apply = apply
        self.counts: Counter[str] = Counter()
        self.results: Counter[str] = Counter()  # the resolver's codes, and written / no_op / would_write
        self.rejected: Counter[str] = Counter()

    def reject(self, code: str, number: int = 1) -> None:
        self.rejected[code] += number

    @property
    def ok(self) -> bool:
        """Red only for what needs fixing by hand. A service that pushes back is not red: those links wait."""
        return not self.rejected

    @property
    def needs_attention(self) -> bool:
        """Also alerted: links about to fall out of the 3-day look-back unresolved."""
        return not self.ok or self.counts["expiring"] > 0

    def line(self) -> str:
        mode = "applied" if self.apply else "probe"
        seen = ", ".join(f"{k} {self.counts[k]}" for k in COUNT_ORDER)
        done = "".join(f", {code} {n}" for code, n in sorted(self.results.items()))
        stuck = "".join(f", {code} {n}" for code, n in sorted(self.rejected.items()))
        return f"news resolve ({mode}): {seen}{done}{stuck}"

    def alert_text(self) -> str:
        return (
            codes.RESOLUTION_CONFLICT + ": a resolution file exists with other bytes; investigate"
            if (codes.RESOLUTION_CONFLICT in self.rejected)
            else self.line()
        )
