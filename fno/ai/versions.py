"""The registered version of each AI book's forecast (stories F1 and G5, design D6): its prompt file, the prompt's
SHA-256, the model the routine must run on and Hybrid's envelope width. A prompt changes only as a new version (a new
file and a new entry here); `brief` refuses a prompt whose bytes differ from the registered hash, so a quiet edit can
never reach a counted forecast."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from ..constants import BOOK2_HYBRID, BOOK3_AI, FORECAST_QUESTIONS, ISOLATION_SEALED_SAME_DAY
from ..forecast_v4.terms import FAMILY_QUESTIONS
from .run_terms import FORECAST_PROTOCOL_V2, FORECAST_PROTOCOL_V4

V4_AI_QUESTIONS = FAMILY_QUESTIONS  # what prompt v2 defines: every family question the rules slot answers (G11 C1)


class VersionRefused(ValueError):
    """The book, version or prompt is not the registered one."""


@dataclass(frozen=True)
class BookVersion:
    book: str
    number: int
    prompt_file: str  # repository path of the versioned prompt
    prompt_sha256: str
    registered_model: str  # the routine's model; a different served model leaves the day unscored (D6)
    envelope_width: float | None  # Hybrid: how far outside the baselines' range it may go; None: no envelope
    isolation: str = ISOLATION_SEALED_SAME_DAY  # how the routine is isolated: part of the version (D6)
    questions: tuple[str, ...] = FORECAST_QUESTIONS  # what its prompt defines; it is never asked anything else
    protocol: str = FORECAST_PROTOCOL_V2  # the protocol it answers: v2 and v4 run side by side until the v4 freeze
    point_envelope_width: float | None = None  # Hybrid, v4's point questions: the relative widening (G11 C3)

    @property
    def forecaster(self) -> str:
        """The registered forecaster's name, e.g. `book3_ai_v2`: protocol v4's slot ledger name and record folder."""
        return f"{self.book}_v{self.number}"

    @property
    def label(self) -> str:
        """`method_or_version` of every record (like Book 1's `book1/v1/sha256:<method hash>`), with the isolation
        mode, so every record carries it (owner's condition 2, 14 Oct 2026)."""
        return f"{self.book}/v{self.number}/sha256:{self.prompt_sha256}/isolation:{self.isolation}"

    def prompt_text(self, root: Path) -> str:
        data = (Path(root) / self.prompt_file).read_bytes()
        if hashlib.sha256(data).hexdigest() != self.prompt_sha256:
            raise VersionRefused(f"{self.prompt_file} differs from version {self.number}: a change needs a new version")
        return data.decode("utf-8")


VERSIONS = (
    BookVersion(BOOK2_HYBRID, 1, "agents/forecast/book2_hybrid_v1.md",
                "8f860d90e2d623763198f4764b1e6ff04fdd7ec7c2fd374c66892542c65505af", "claude-opus-5-5", 0.10),
    BookVersion(BOOK3_AI, 1, "agents/forecast/book3_ai_v1.md",
                "6917786dac7430c951a7f80027b8d7c5ba40701d21288aebe7cfadccad77259a", "claude-opus-5-5", None),
    BookVersion(BOOK2_HYBRID, 2, "agents/forecast/book2_hybrid_v2.md",
                "c73e452042326029c6af757b303edf7db398b27da69df652f5699fe362368165", "claude-opus-5-5", 0.10,
                questions=V4_AI_QUESTIONS, protocol=FORECAST_PROTOCOL_V4, point_envelope_width=0.25),
    BookVersion(BOOK3_AI, 2, "agents/forecast/book3_ai_v2.md",
                "8f9dd780f81223cb5856b3ea76d6a3586c02c5a1eeedd1e9adb078672bb2f3cd", "claude-opus-5-5", None,
                questions=V4_AI_QUESTIONS, protocol=FORECAST_PROTOCOL_V4),
)  # fmt: skip


def current_version(book: str, protocol: str = FORECAST_PROTOCOL_V2) -> BookVersion:
    """The newest registered version of the book's forecast for `protocol` (a v4 version never answers v2)."""
    found = [v for v in VERSIONS if v.book == book and v.protocol == protocol]
    if not found:
        raise VersionRefused(f"{book!r} has no registered {protocol} version")
    return max(found, key=lambda v: v.number)


def version_by_label(label: str) -> BookVersion:
    for version in VERSIONS:
        if version.label == label:
            return version
    raise VersionRefused(f"{label!r} is not a registered version")
