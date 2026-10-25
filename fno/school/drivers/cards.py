"""Driver card files (story MS-P1e): `research/school/cards/<code>_v<version>.yaml`. A card is a frozen file; its
SHA-256 goes into every decision record. Until MS-P1h freezes them the files are drafts."""

import hashlib
from pathlib import Path

import yaml

from ..constants import DriverRole, RoadCode
from ..contracts.decisions import DriverCard
from .card_params import CardError, parameters_of

CARD_KEYS = {"code", "version", "family", "role", "roads", "band_steps", "parameters"}
CARDS_FOLDER = Path("research") / "school" / "cards"


def load_card(path: Path) -> DriverCard:
    raw = path.read_bytes()
    document = yaml.safe_load(raw)
    if not isinstance(document, dict) or set(document) != CARD_KEYS:
        raise CardError(f"{path.name}: a card holds exactly {sorted(CARD_KEYS)}")
    try:
        card = DriverCard(
            code=str(document["code"]),
            version=str(document["version"]),
            family=str(document["family"]),
            role=DriverRole(document["role"]),
            roads=tuple(RoadCode(r) for r in document["roads"]),
            band_steps=int(document["band_steps"]),
            parameters=parameters_of(document["parameters"] or {}),
            card_sha256=hashlib.sha256(raw).hexdigest(),
        )
    except (ValueError, TypeError) as problem:
        raise CardError(f"{path.name}: {problem}") from problem
    if path.name != f"{card.code}_v{card.version}.yaml":
        raise CardError(f"{path.name}: the file name must be {card.code}_v{card.version}.yaml")
    return card


def load_cards(folder: Path) -> dict[str, DriverCard]:
    """Every card in the folder by driver code; two files for one code are an error (one version per code at a time)."""
    cards: dict[str, DriverCard] = {}
    for path in sorted(folder.glob("*.yaml")):
        card = load_card(path)
        if card.code in cards:
            raise CardError(f"{path.name}: a second card for {card.code}")
        cards[card.code] = card
    return cards
