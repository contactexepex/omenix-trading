"""No private account figure in an AI book's answer (story F1t criterion 3d, judge 301). The reveal is public and the
book's reason is copied into its public D3 record, while E2c keeps the accounts (fills, cash, P&L) in Drive only.
So every text of the answer is refused if it holds a number that appears in the book's private pack outside its
public folders and nowhere in the common pack. Only numbers of at least 3 digits, or with a decimal part, count
(a "1 lot" or "20 days" is not a figure). Indian and western digit grouping (1,25,000 and 125,000) and the rupee
prefixes (Rs, Rs., INR, ₹) are normalised first, so a figure cannot slip past by its writing. The check is
conservative: a number of the book's own past public records that the common pack lacks is refused too, and the
model writes the sentence without it. Standard library only (it runs in the routine's `seal`)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from decimal import Decimal, InvalidOperation

NUMBER = re.compile(r"(?<![\w.])(?:₹|Rs\.?|INR)?\s?(?P<whole>\d{1,3}(?:,\d{2,3})+|\d+)(?P<fraction>\.\d+)?(?![\w])")
MIN_DIGITS = 3


def figures(text: str) -> set[str]:
    """The text's counted numbers, each in one canonical form ("1,25,000.50" and "125000.5" are the same)."""
    found = set()
    for match in NUMBER.finditer(text):
        whole, fraction = match["whole"].replace(",", ""), match["fraction"] or ""
        if len(whole.lstrip("0")) < MIN_DIGITS and not fraction:
            continue
        try:
            value = Decimal(whole + fraction)
        except InvalidOperation:
            continue
        found.add(format(value.normalize(), "f"))
    return found


def private_figures(private_pack: dict, common_pack_text: str, public_folders: Iterable[str]) -> set[str]:
    """Numbers in the private pack's files outside `public_folders` that the common pack does not hold."""
    public = tuple(folder.rstrip("/") + "/" for folder in public_folders)
    private = set()
    for file in private_pack.get("files", []):
        if not str(file.get("path", "")).startswith(public):
            private |= figures(str(file.get("text", "")))
    return private - figures(common_pack_text)


def texts(value, place: str = "decision") -> Iterator[tuple[str, str]]:
    """Every text inside an answer object, with where it is (`decision.trades[0].reason`)."""
    if isinstance(value, str):
        yield place, value
    elif isinstance(value, dict):
        for key in sorted(value):
            yield from texts(value[key], f"{place}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from texts(item, f"{place}[{index}]")


def figure_problems(decision: dict, private: set[str]) -> list[str]:
    """Where the answer quotes a private figure; the figure itself is never repeated in the message."""
    return [f"{place} quotes a private account figure (fill, cash or P&L from your private pack): write it without "
            f"that number" for place, text in texts(decision) if figures(text) & private]  # fmt: skip


REDACTED = "[private figure]"


def redact(text: str, private: set[str]) -> str:
    """The text with every private figure replaced (a decider's or shape check's message may quote one; outcome
    records are public and their reasons are alerted)."""
    return NUMBER.sub(lambda m: REDACTED if figures(m.group(0)) & private else m.group(0), text)
