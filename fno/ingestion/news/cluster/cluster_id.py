"""Cluster ids (P2c; design D5): the SHA-256 of the earliest member's key (earliest by story time, ties by the smaller
key), so the id is a hash and carries nothing of the story. When a later-arriving earlier article, or an anchor that
left the window, changes an id, the new cluster names the ids it replaces, so a reader can follow a story across runs.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence


def cluster_id(anchor_key: str) -> str:
    return hashlib.sha256(anchor_key.encode("ascii")).hexdigest()


def replaced_ids(
    new_id: str, member_keys: Iterable[str], previous: Sequence[tuple[str, frozenset[str]]]
) -> tuple[str, ...]:
    """The earlier run's cluster ids (each with its members) that share a member with this cluster under another id."""
    members = frozenset(member_keys)
    return tuple(sorted({old for old, old_members in previous if old != new_id and old_members & members}))
