"""Sealed answers (story F1's isolation between the two AI books): before 15:15 a book publishes only a commitment,
the SHA-256 of a random salt and its answer, which reveals nothing; after 15:15 it publishes the answer and the salt.
The reveal must hash to the commitment, so nothing can change once sealed, and neither book can read the other's
answer before its own commitment is in."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass

from .export import canonical

SALT = re.compile(r"[0-9a-f]{32}")  # 128 random bits: the answer cannot be guessed from the commitment
COMMITMENT_FIELDS = ("book", "commitment_sha256", "day", "export_sha256", "version")


class SealBroken(ValueError):
    """A reveal that does not match its commitment, or a file of the wrong shape."""


def new_salt() -> str:
    return secrets.token_hex(16)


def commitment_hash(salt: str, answer: dict) -> str:
    return hashlib.sha256(salt.encode("ascii") + b":" + canonical(answer)).hexdigest()


@dataclass(frozen=True)
class Commitment:
    book: str
    day: str
    version: str
    export_sha256: str
    commitment_sha256: str

    @classmethod
    def of(cls, answer: dict, salt: str) -> Commitment:
        return cls(answer["book"], answer["day"], answer["version"], answer["export_sha256"],
                   commitment_hash(salt, answer))  # fmt: skip

    def to_text(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, indent=1) + "\n"

    @classmethod
    def from_text(cls, text: str) -> Commitment:
        try:
            fields = json.loads(text)
        except ValueError:
            raise SealBroken("the commitment is not JSON") from None
        if not isinstance(fields, dict) or sorted(fields) != list(COMMITMENT_FIELDS):
            raise SealBroken(f"the commitment must have exactly {', '.join(COMMITMENT_FIELDS)}")
        if not all(isinstance(value, str) for value in fields.values()):
            raise SealBroken("every commitment field must be text")
        return cls(**fields)


def reveal_text(answer: dict, salt: str) -> str:
    return json.dumps({"answer": answer, "salt": salt}, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def open_reveal(text: str, commitment: Commitment) -> dict:
    """The answer inside a reveal, once its hash matches the commitment; SealBroken otherwise."""
    try:
        fields = json.loads(text)
    except ValueError:
        raise SealBroken("the reveal is not JSON") from None
    if not isinstance(fields, dict) or sorted(fields) != ["answer", "salt"]:
        raise SealBroken("the reveal must have exactly answer and salt")
    if not isinstance(fields["salt"], str) or not SALT.fullmatch(fields["salt"]):
        raise SealBroken("the salt is not 32 hex characters")
    if commitment_hash(fields["salt"], fields["answer"]) != commitment.commitment_sha256:
        raise SealBroken("the reveal does not hash to the commitment")
    return fields["answer"]
