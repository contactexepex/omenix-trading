"""The pin of a private versioned file against the version a run used before (NP7b; shared by NP8): one rule for every
run that must not go behind, or find changed, the list or terms the last good run used. An older version is a
rollback; the same version with other bytes is a file edited in place (a version number alone would not show it); a
newer version is simply a new file. Nothing to compare with before the first run (`last_version` 0)."""

from __future__ import annotations


def pin_violation(
    version: int, sha256: str, last_version: int, last_sha256: str, rolled_back: str, damaged: str
) -> str:
    """The fixed code to stop (or degrade) with, or "" when the file may be used."""
    if not last_version:
        return ""
    if version < last_version:
        return rolled_back
    if version == last_version and sha256 != last_sha256:
        return damaged
    return ""
