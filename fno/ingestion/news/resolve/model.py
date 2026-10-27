"""The link resolver's vocabulary (NP2b): one fixed code per link, never the link, never a library message."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

RESOLVED = "resolved"
REFUSED_LINK = "refused_link"  # the link is not https on the allowed domain: never requested
DECODE_FAILED = "decode_failed"  # the service answered but gave no URL (a changed link, a block, a changed protocol)
BAD_RESULT = (
    "bad_result"  # a URL came back that we will not keep (not a clean https link, or back on the service itself)
)
ERROR = "error"  # the library or the network raised
PAUSED = (
    "paused"  # the service pushed back earlier in this run: nothing more is requested, the link waits for the next run
)
CODES = (RESOLVED, REFUSED_LINK, DECODE_FAILED, BAD_RESULT, ERROR, PAUSED)


@dataclass(frozen=True)
class Resolved:
    code: str
    url: str = ""  # only with code RESOLVED


class LinkResolver(ABC):
    """Turns redirect links into the publisher's own URLs. One `Resolved` per link, in the same order, always."""

    @abstractmethod
    def resolve(self, links: Sequence[str]) -> list[Resolved]: ...
