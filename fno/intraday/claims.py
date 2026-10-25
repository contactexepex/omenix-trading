"""One taker per mark (story O9 section 6). Two recorders on one Groww key exceed its rate limit: on 16 Oct every
mark taken by two runs lost 74-87 of about 224 quotes (Groww code 429), every mark taken by one run lost none. Before a
mark a run commits a claim file to GitHub; git's push decides atomically (the second push meets the first one's file
and keeps it, the committer's first-push-wins rule), so exactly one run sees its own claim. A run that cannot claim at
all (GitHub unreachable, push refused) does not take the mark (story GW1): it cannot know whether another run holds
it, and two takers exceed Groww's 300 a minute. A16's fires overlap, so another run whose push lands takes it; a mark
is lost only when every living run fails to claim it."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..models import IST
from ..storage.manifest_commit import COMMITTED_AS, NOTHING_AS, ManifestRecorder

CLAIM_MESSAGE = "Claim: A16 mark ({what})"
CLAIM_LABEL = "claim"
WON, LOST, UNCLAIMED = "won", "lost", "unclaimed"  # unclaimed: the claim could not be made; the run does not take it


@dataclass(frozen=True)
class ClaimResult:
    outcome: str
    holder: str  # the run that holds the claim (empty when unclaimed)
    detail: str = ""

    @property
    def take(self) -> bool:
        return self.outcome == WON


class MarkClaims(ABC):
    @abstractmethod
    def claim(self, day: date, mark: datetime) -> ClaimResult:
        """Claims the mark for this run, or says which run holds it."""


class NoClaims(MarkClaims):
    """A dry run, or a single host: every mark is this run's."""

    def claim(self, day: date, mark: datetime) -> ClaimResult:
        return ClaimResult(WON, "")


class GitMarkClaims(MarkClaims):
    def __init__(self, folder: Path, committer: ManifestRecorder, run_id: str, clock):
        """`folder`: the claims tree in the checkout; `committer`: commits only that tree, first push wins."""
        self.folder, self.committer, self.run_id, self.clock = Path(folder), committer, run_id, clock

    def file_for(self, day: date, mark: datetime) -> Path:
        return self.folder / f"{day:%Y-%m-%d}" / f"{mark.astimezone(IST):%H%M}.json"

    def claim(self, day: date, mark: datetime) -> ClaimResult:
        file = self.file_for(day, mark)
        if not file.is_file():
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(json.dumps({"run_id": self.run_id, "claimed_at": self.clock().isoformat()}) + "\n")
        outcome = self.committer.commit(f"{day:%Y-%m-%d} {mark.astimezone(IST):%H:%M}")
        if outcome == NOTHING_AS.format(label=CLAIM_LABEL):
            outcome = self.committer.publish()  # committed by an earlier try: it counts only once pushed (GW1)
        holder = _holder(file)
        if holder == self.run_id and not _published(outcome):
            return ClaimResult(UNCLAIMED, "", outcome)  # never reached GitHub: another run may hold it unseen
        return ClaimResult(WON if holder == self.run_id else LOST, holder, outcome)


def _published(outcome: str) -> bool:
    """The committer pushed the claim now, or pushed the checkout holding it (an earlier try's commit, or one already
    on GitHub): after that push the file is the copy GitHub keeps."""
    return outcome in (COMMITTED_AS.format(label=CLAIM_LABEL, count=1), COMMITTED_AS.format(label=CLAIM_LABEL, count=0))


def _holder(file: Path) -> str:
    try:
        return json.loads(file.read_text())["run_id"]
    except (OSError, ValueError, KeyError):
        return ""
