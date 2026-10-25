"""Seal checking (story 3.4, criterion 2): the fill port asks this before any fill. A seal that is not on the remote,
was pushed after the fill time or names another file's SHA-256 is refused (`stale_seal`)."""

from datetime import datetime

from ...storage.receipt_publisher import ReceiptPublisher, SealNotPushed
from ..contracts.seal import Seal, StaleSeal

OTHER_FILE = "seal {path} names another file than the decisions the fill rests on"
PUSHED_LATE = "seal {path} was pushed at {pushed}, after the fill time {fill}"
NOT_PUSHED = "seal {path} is not on the remote: commit {commit} does not hold this file's receipt as sealed"


class SealChecker:
    def __init__(self, publisher: ReceiptPublisher, area: str):
        self.publisher, self.area = publisher, area

    def check(self, seal: Seal, file_sha256: str, fill_time: datetime) -> None:
        """Returns when the seal covers the file and was pushed no later than the fill; else raises `StaleSeal`."""
        if seal.sha256 != file_sha256:
            raise StaleSeal(OTHER_FILE.format(path=seal.path))
        if not seal.covers(file_sha256, fill_time):
            raise StaleSeal(PUSHED_LATE.format(path=seal.path, pushed=seal.pushed_at, fill=fill_time))
        try:
            pushed = self.publisher.published(f"{self.area}/{seal.path}")
        except SealNotPushed as unreadable:  # a shallow clone that cannot be deepened: refused by name
            raise StaleSeal(str(unreadable)) from unreadable
        if pushed is None or (pushed.commit, pushed.sha256, pushed.pushed_at) != (
            seal.commit,
            seal.sha256,
            seal.pushed_at,
        ):
            raise StaleSeal(NOT_PUSHED.format(path=seal.path, commit=seal.commit))
