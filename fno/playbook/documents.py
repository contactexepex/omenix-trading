"""Reading a playbook file's text into a strategy, naming the file in every refusal."""

from __future__ import annotations

import yaml

from .fields import PlaybookError
from .schema import Strategy, parse_strategy


def strategy_from_text(text: str, where: str) -> Strategy:
    """The strategy in a file's text; PlaybookError naming `where` and the field otherwise."""
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as bad:
        raise PlaybookError(where, f"not valid YAML: {bad}") from None
    try:
        return parse_strategy(document)
    except PlaybookError as refused:
        raise PlaybookError(f"{where}: {refused.field}", refused.reason) from None
