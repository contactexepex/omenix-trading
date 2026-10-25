"""What the daily run fires each AI book's decision routine with (story F1t): one line of JSON naming the book, the
day, the book's registered decision version and the common pack's SHA-256, carrying the book's own E2 private pack
(the session cannot read Drive) and F2's `analyst_cards` item. Its own parser with a 64 KiB cap, never the forecast
pointer's 4 KiB one. The routine receives it as untrusted text, so reading it back checks every field and refuses
anything else before any input is shown to the model."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import ROUTINE_POINTER_MAX_BYTES
from ..desk.pack_items import canonical_json, sha256_hex
from .versions import DecisionRegistry, VersionRefused

KIND = "decision"
FIELDS = ("analyst_cards", "book", "common_pack_sha256", "day", "kind", "private_pack", "private_pack_sha256",
          "receipt_deadline", "reveal_from", "version")  # fmt: skip
CARD_FIELDS = ("day", "input_sha256", "role_set_version", "roles")  # F2's item (agreed 16 Oct)
MAX_POINTER_BYTES = ROUTINE_POINTER_MAX_BYTES  # one home with G11's v4 pointer; confirmed at the go-live fire
SHA256 = re.compile(r"[0-9a-f]{64}")


class PointerRefused(ValueError):
    """The text is not a decision pointer this project wrote; the message names the first thing wrong."""


@dataclass(frozen=True)
class DecisionPointer:
    book: str
    day: date
    version: str  # the registered decision version's label
    common_pack_sha256: str
    private_pack: dict  # the book's E2 private pack body, exactly as built
    analyst_cards: dict  # F2's item: role_set_version, input_sha256, roles (status lines; cards when usable)
    receipt_deadline: datetime  # the routine reads no config: the runner's times travel with the pointer
    reveal_from: datetime

    @property
    def private_pack_sha256(self) -> str:
        return sha256_hex(canonical_json(self.private_pack))

    def to_text(self) -> str:
        fields = {
            "analyst_cards": self.analyst_cards,
            "book": self.book,
            "common_pack_sha256": self.common_pack_sha256,
            "day": self.day.isoformat(),
            "kind": KIND,
            "private_pack": self.private_pack,
            "private_pack_sha256": self.private_pack_sha256,
            "receipt_deadline": self.receipt_deadline.isoformat(),
            "reveal_from": self.reveal_from.isoformat(),
            "version": self.version,
        }
        return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def size(self) -> int:
        return len(self.to_text().encode("utf-8"))


def parse_pointer(text: str, registry: DecisionRegistry) -> DecisionPointer:
    if len(text.encode("utf-8")) > MAX_POINTER_BYTES:
        raise PointerRefused(f"longer than {MAX_POINTER_BYTES} bytes")
    try:
        fields = json.loads(text)
    except ValueError as error:
        raise PointerRefused(f"not JSON ({error.msg})") from None
    if not isinstance(fields, dict) or sorted(fields) != list(FIELDS):
        raise PointerRefused(f"fields must be exactly {', '.join(FIELDS)}")
    if fields["kind"] != KIND:
        raise PointerRefused(f"kind must be {KIND!r}")
    try:
        version = registry.current(fields["book"] if isinstance(fields["book"], str) else "")
        day = date.fromisoformat(fields["day"])
    except (VersionRefused, TypeError, ValueError) as error:
        raise PointerRefused(str(error)) from None
    if fields["version"] != version.label:
        raise PointerRefused("version is not the book's registered decision version")
    times = (_moment(fields, name, day) for name in ("receipt_deadline", "reveal_from"))
    pointer = DecisionPointer(fields["book"], day, version.label, _sha(fields, "common_pack_sha256"),
                              _private_pack(fields, day), _cards(fields["analyst_cards"], day), *times)  # fmt: skip
    if pointer.private_pack_sha256 != _sha(fields, "private_pack_sha256"):
        raise PointerRefused("the private pack does not hash to private_pack_sha256")
    return pointer


def _sha(fields: dict, name: str) -> str:
    value = fields[name]
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise PointerRefused(f"{name} is not a SHA-256")
    return value


def _moment(fields: dict, name: str, day: date) -> datetime:
    try:
        moment = datetime.fromisoformat(fields[name])
    except (TypeError, ValueError):
        raise PointerRefused(f"{name} is not a time") from None
    if moment.tzinfo is None or moment.date() != day:
        raise PointerRefused(f"{name} must be a time on {day} with its zone")
    return moment


def _private_pack(fields: dict, day: date) -> dict:
    pack = fields["private_pack"]
    if not isinstance(pack, dict) or pack.get("book") != fields["book"] or pack.get("day") != day.isoformat():
        raise PointerRefused("the private pack is not this book's pack for this day")
    return pack


def _cards(item, day: date) -> dict:
    if not isinstance(item, dict) or sorted(item) != list(CARD_FIELDS) or not isinstance(item["roles"], list):
        raise PointerRefused(f"analyst_cards must have exactly {', '.join(CARD_FIELDS)}, roles a list")
    if item["day"] != day.isoformat():
        raise PointerRefused("analyst_cards are not this day's")
    return item
