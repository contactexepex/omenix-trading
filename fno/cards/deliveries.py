"""The card's delivery metadata in the public repository (story T1): one file per posting attempt,
`research/cards/deliveries/<YYYY>/<d>-a<n>.json`, never rewritten. It holds only non-sensitive facts: status, reason
code, the card's SHA-256, the hashes of the committed records used, Slack's `ts` and outcome, the Drive outcome and
the clock checks. Never the card text (that stays in Drive, owner decision of 15 Oct 2026). Committing it gives the
GitHub push receipt, the second issuance witness (design 04 section 4.4). Earlier deliveries are read as committed,
so the next card can name a miss."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from ..constants import CARD_DELIVERIES_FOLDER
from .committed import CommittedRecords

DELIVERY_FILE = re.compile(r"(\d{4}-\d{2}-\d{2})-a(\d+)\.json")
NO_CARD = "no card on record for {day}"
NOT_SENT = "the {day} card was NOT sent ({outcome})"
NOT_SAVED = "the {day} card record was NOT saved to Drive ({outcome})"
CLOCK = "the {day} card's clock check gave a WARNING ({servers})"
UNCHECKED = "the {day} card's {line}"


def delivery_path(day: date, attempt: int) -> str:
    return f"{CARD_DELIVERIES_FOLDER}/{day:%Y}/{day.isoformat()}-a{attempt}.json"


class DeliveryLog(ABC):
    @abstractmethod
    def write(self, day: date, metadata: dict) -> str:
        """Write a new attempt's metadata; returns its repository path. Never overwrites an attempt."""

    @abstractmethod
    def attempts(self, day: date) -> list[tuple[str, dict]]:
        """The committed attempts of a day, oldest first: (repository path, metadata)."""


class RepoDeliveryFiles(DeliveryLog):
    def __init__(self, root: Path, committed: CommittedRecords):
        self.root, self.committed = Path(root), committed

    def _numbers(self, day: date) -> list[int]:
        folder = self.root / CARD_DELIVERIES_FOLDER / f"{day:%Y}"
        found = (DELIVERY_FILE.fullmatch(p.name) for p in folder.glob(f"{day.isoformat()}-a*.json"))
        return sorted(int(m.group(2)) for m in found if m)

    def write(self, day: date, metadata: dict) -> str:
        committed = [int(m.group(2)) for m in map(DELIVERY_FILE.fullmatch, self._committed_names(day)) if m]
        path = delivery_path(day, max([*self._numbers(day), *committed], default=0) + 1)
        target = self.root / path
        body = json.dumps(metadata, indent=1, sort_keys=True) + "\n"  # first: a failure leaves no empty attempt file
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as out:  # "x": an existing attempt is never rewritten
            out.write(body)
        return path

    def _committed_names(self, day: date) -> list[str]:
        names = self.committed.names(f"{CARD_DELIVERIES_FOLDER}/{day:%Y}")
        return [n for n in names if n.startswith(f"{day.isoformat()}-a")]

    def attempts(self, day: date) -> list[tuple[str, dict]]:
        names = self._committed_names(day)
        numbers = sorted(
            int(m.group(2)) for m in map(DELIVERY_FILE.fullmatch, names) if m and m.group(1) == day.isoformat()
        )
        found = [(path, self.committed.read(path)) for path in (delivery_path(day, n) for n in numbers)]
        return [(path, json.loads(data)) for path, data in found if data is not None]


def misses(log: DeliveryLog, day: date) -> tuple[str, ...]:
    """What went wrong with a session's card, as the next card states it (design 4.1: "the next card says so")."""
    attempts = [metadata for _, metadata in log.attempts(day) if not metadata.get("test")]  # a test is not the card
    if not attempts:
        return (NO_CARD.format(day=day),)
    sent = [a for a in attempts if a["slack"]["sent"]]
    found = [] if sent else [NOT_SENT.format(day=day, outcome=attempts[-1]["slack"]["outcome"])]
    last = (sent or attempts)[-1]
    if not last["drive"]["saved"]:
        found.append(NOT_SAVED.format(day=day, outcome=last["drive"]["outcome"]))
    warned = [c["server"] for c in last["clock"] if c["warning"]]
    if warned:
        found.append(CLOCK.format(day=day, servers=", ".join(warned)))
    if last["slack"]["sent"]:  # on a sent card every server was asked: an unchecked one is a named miss
        found += [UNCHECKED.format(day=day, line=c["line"]) for c in last["clock"] if c.get("checked") is False]
    return tuple(found)
