"""What one `news read-pages` run did: counts and fixed codes only, never a title, a link, a key or a host."""

from __future__ import annotations

from collections import Counter

COUNT_ORDER = ("examined", "already", "unresolved", "unlisted", "no_link", "asked", "budget_stopped", "unexamined")


class ReadReport:
    def __init__(self, apply: bool) -> None:
        self.apply = apply
        self.counts: Counter[str] = Counter()
        self.pages: Counter[str] = Counter()  # the fetcher's fixed codes, then no_facts / written / no_op / would_write
        self.rejected: Counter[str] = Counter()

    def reject(self, code: str, number: int = 1) -> None:
        self.rejected[code] += number

    @property
    def ok(self) -> bool:
        return not self.rejected

    @property
    def needs_attention(self) -> bool:
        """Also alerted: articles the read cap left unread, or a run that stopped on its time budget."""
        return not self.ok or self.counts["unexamined"] > 0 or self.counts["budget_stopped"] > 0

    def line(self) -> str:
        mode = "applied" if self.apply else "probe"
        seen = ", ".join(f"{k} {self.counts[k]}" for k in COUNT_ORDER)
        pages = "".join(f", {code} {n}" for code, n in sorted(self.pages.items()))
        stuck = "".join(f", {code} {n}" for code, n in sorted(self.rejected.items()))
        return f"news read-pages ({mode}): {seen}{pages}{stuck}"
