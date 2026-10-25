"""Where the index list comes from: an interface and NSE's public adapter (read-only, no Groww, never an order)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable

from .constants import ALL_INDICES_PATH


class CloseListSource(ABC):
    @abstractmethod
    def answer(self) -> tuple[dict, bytes]:
        """The parsed answer and the bytes kept as its raw file."""


class NseIndexList(CloseListSource):
    def __init__(self, nse_json: Callable[[str, dict | None], dict]):
        self.nse_json = nse_json

    def answer(self) -> tuple[dict, bytes]:
        """The shared client returns the parsed answer, so the raw file is its canonical JSON (sorted keys): the
        SHA-256 in the record is of those bytes, not of NSE's own byte stream."""
        payload = self.nse_json(ALL_INDICES_PATH, None)
        return payload, json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
