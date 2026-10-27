"""Comparing source labels (NP1): the text a feed gives for an outlet, brought to one form."""

from __future__ import annotations

import re


def normalise_label(label: str | None) -> str:
    """Spaces collapsed, curly apostrophes straightened, lower case, without a leading 'by ' or trailing dots."""
    return re.sub(r"\s+", " ", (label or "").replace("’", "'")).strip().lower().removeprefix("by ").strip(" .")
