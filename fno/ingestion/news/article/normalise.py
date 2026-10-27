"""Text as it is compared (P2b): Unicode-normalised, case-folded, white space collapsed. Used for keys and for
comparing an article with its later copy, never for what is stored (the file keeps the text as the feed gave it)."""

from __future__ import annotations

import unicodedata


def normalise(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text or "").casefold().split())
