"""A sealed record named by path and SHA-256 (story REC1a): the recommendation's inputs, the day's candidates and
the frozen reports that back a version's rung all point to what they rest on this way."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RecordRef:
    path: str
    sha256: str
