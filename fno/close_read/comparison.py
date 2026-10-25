"""A4h-2's field-by-field comparison of two reads (or a read and the official file), as `same` / `differs by X` or a
confirm status: never a level. A field one side lacks (an older record, INDIA VIX's `null`) is left out."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .answer import difference


def compared(mine: dict, theirs: dict, fields: Iterable[str],
             status: Callable[[float, float], str] = difference) -> dict[str, str]:  # fmt: skip
    """Each field both sides hold, by `status`."""
    return {key: status(mine[key], theirs[key]) for key in fields
            if mine.get(key) is not None and theirs.get(key) is not None}  # fmt: skip


def changed(statuses: dict[str, str], unchanged: str = "same") -> str:
    """The fields whose status is not `unchanged`, as " (high differs by 0.05)", or ""."""
    moved = [f"{key} {status}" for key, status in statuses.items() if status != unchanged]
    return f" ({', '.join(moved)})" if moved else ""
