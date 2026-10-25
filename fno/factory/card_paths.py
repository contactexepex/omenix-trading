"""Where a registered idea card lives (story R1): `research/ideas/<id>.md`, or the path its ledger row names. A ledger
row's `protocol_path` is usually a protocol file (experiments, GR1, EDGE1) and so holds no ```factory block; one that
holds the block is an idea card kept beside its own story (the market school's comparison card), and every reader of
cards finds it the same way as one in the ideas folder. A card with the block that cannot be read is an error, never
skipped."""

from __future__ import annotations

import re
from pathlib import Path

from ..research_engine.ledger import Ledger
from .constants import CARD_FENCE, IDEAS_FOLDER, TEMPLATE_CARD
from .fields import CardError

_BLOCK_START = re.compile(rf"^```{CARD_FENCE}$", re.MULTILINE)


def ideas_folder_paths(root: Path) -> list[str]:
    folder = Path(root) / IDEAS_FOLDER
    return sorted(p.relative_to(root).as_posix() for p in folder.glob("*.md") if p.name != TEMPLATE_CARD)


def ledger_card_paths(root: Path) -> list[str]:
    """Card files outside the ideas folder that the ledger names, each holding a ```factory block. A .md file the
    ledger names that is not in the repository raises by name: skipping it would leave a missing card's trial counted
    as a test."""
    named = sorted({row["protocol_path"] for row in Ledger(root).rows() if row["protocol_path"].endswith(".md")})
    missing = [path for path in named if not (Path(root) / path).is_file()]
    if missing:
        raise CardError(f"{missing[0]}: named by the ledger but not in the repository")
    outside = (path for path in named if not path.startswith(f"{IDEAS_FOLDER}/"))
    return [path for path in outside if _holds_block(Path(root) / path)]


def all_card_paths(root: Path) -> list[str]:
    """The ideas folder first; a card elsewhere whose id is also in the ideas folder is that same card (the ideas
    folder wins, it is returned once). Two cards elsewhere with one id are ambiguous and raise."""
    paths = ideas_folder_paths(root)
    in_ideas = {Path(path).stem for path in paths}
    elsewhere: dict[str, str] = {}
    for path in ledger_card_paths(root):
        card_id = Path(path).stem
        if card_id in in_ideas:
            continue
        if card_id in elsewhere:
            raise CardError(f"{path}: the id {card_id!r} is also {elsewhere[card_id]}")
        elsewhere[card_id] = path
    return [*paths, *elsewhere.values()]


def card_path(idea_id: str, root: Path) -> str:
    """The ideas folder first (unchanged), else the ledger-named card whose file name is the id."""
    in_ideas = f"{IDEAS_FOLDER}/{idea_id}.md"
    if (Path(root) / in_ideas).is_file():
        return in_ideas
    return next((path for path in ledger_card_paths(root) if Path(path).stem == idea_id), in_ideas)


def _holds_block(file: Path) -> bool:
    return file.is_file() and _BLOCK_START.search(file.read_text(encoding="utf-8")) is not None
