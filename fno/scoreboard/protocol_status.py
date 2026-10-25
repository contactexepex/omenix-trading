"""The evaluation protocol's status as scoreboard B states it (story S2): the protocol version and whether its freeze
record is committed (S1). Whether the frozen files are unchanged since is S1's own check (`evaluation verify`)."""

from __future__ import annotations

from pathlib import Path

from ..evaluation.freeze import freeze_path
from ..evaluation.protocol import PROTOCOL_FILE, parse_protocol
from .ports import ProtocolStatus


def protocol_status(root: Path) -> ProtocolStatus:
    path = Path(root) / PROTOCOL_FILE
    version = parse_protocol(path.read_text(encoding="utf-8")).version if path.is_file() else None
    if version is None:
        return ProtocolStatus(None, False)
    return ProtocolStatus(version, (Path(root) / freeze_path(version)).is_file())
