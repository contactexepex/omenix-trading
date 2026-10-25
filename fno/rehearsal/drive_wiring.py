"""The owner Drive's rehearsal form (story REH1), chosen by `build_owner_drive`: unchanged in a real run, the dryrun
store over the real one when rehearsing. Apart from the Slack labels, so Drive's import closure stays Drive's."""

from __future__ import annotations

import os
from collections.abc import Mapping

from ..models import now_utc
from ..storage.receipts import ReceiptFolder
from .drive import DryrunDrive
from .manifest_rows import ManifestRows
from .mode import rehearsal
from .quote_sidecars import QuoteSidecars
from .visibility import Visibility

RECEIPTS = "receipts"


def rehearsed_drive(drive, env: Mapping[str, str] = os.environ):
    mode = rehearsal(env)
    if mode is None or drive is None:
        return drive
    visible = Visibility(ReceiptFolder(mode.record / RECEIPTS), now_utc, ManifestRows(mode.record),
                         QuoteSidecars(mode.record))  # fmt: skip
    return DryrunDrive(drive, mode.drive_root, visible)
