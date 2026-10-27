"""Feed provenance (NP11): which feed found which article, kept in the private Record only. Names, the sealing and the
day arithmetic live here; the file bytes are in `file.py`.

The join "this article key was found by that feed id" is the sensitive part: keys are digests of public guids and links,
feed ids are in the public poll log, so a file that is a plain function of those could be rebuilt by a guesser and its
published SHA-256 matched (judge 114). Every provenance file therefore carries a SEAL, an HMAC of its path keyed
with the feed list's private salt: the bytes cannot be rebuilt without the salt, and stay the same for the same salt.
The salt is frozen (planned feed ids depend on it too). Principle for any future file that is a pure function of public
values: seal it before its SHA-256 is published."""

from __future__ import annotations

import hashlib
import hmac
from datetime import date, datetime, timedelta, timezone

FOLDER = "news/provenance/1"
FORMAT = 1
BROAD, TARGETED, UNKNOWN = "broad", "targeted", "unknown"
LABELLED = (BROAD, TARGETED)  # what a feed list may say; a feed with no label is UNKNOWN, never guessed from its id
PROVENANCE_FILE = "provenance.csv"  # the manifest of the provenance files (path, SHA-256, size: no feed id, no key)
IST = timezone(timedelta(hours=5, minutes=30))
SEAL_PREFIX = b"provenance\0"

Pair = tuple[str, str]  # (feed id, scope)
Pairs = dict[str, frozenset[Pair]]  # article key -> the feeds that found it


def day_of(moment: datetime) -> date:
    return moment.astimezone(IST).date()


def path_of(day: date, number: int = 0) -> str:
    """`<day>.json` is the day file, `<day>-<n>.json` its n-th supplement (a late poll): numbered, never a hash."""
    return f"{FOLDER}/{day:%Y-%m-%d}" + (f"-{number}" if number else "") + ".json"


def seal_of(salt: str, path: str) -> str:
    return hmac.new(salt.encode(), SEAL_PREFIX + path.encode(), hashlib.sha256).hexdigest()


def provenance_id(path: str) -> str:
    """The manifest id of a provenance file: its day and number, never a feed or a key."""
    return path.rsplit("/", 1)[-1].removesuffix(".json")
