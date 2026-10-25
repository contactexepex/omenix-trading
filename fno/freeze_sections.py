"""Per-consumer sections of G1 protocol v3's freeze record (orchestrator, after judge 64): one `FREEZE_v3.md`, with one
named section per job that checks it, so a change fails only the job whose files it touches.

- `panel-days` (story A13's daily panel job) checks the appender, the job, its composition root and this module;
- `forecast-scores` (story G4's scoring, when live records exist) checks the files that decide live question 5, the
  replay and this module.

Each section lists the protocol file's hash too. The rules are v2's freeze rules, applied to one section: the protocol
commit and the freeze record are in the history of the running commit; the protocol text at that commit has its
recorded hash; and every file of the section still has its recorded bytes. v2's `require_version_frozen` cannot be
reused as it is: it checks every row of the record, and its file is byte-frozen by v2. So this module reuses its
building blocks (`read_version_freeze`, `changed_files`, `Git`).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .forecast.freeze import Freeze, NotFrozen, changed_files
from .forecast.freeze_v2 import NotYetFrozen, read_version_freeze
from .research_engine.ledger import Git

PROTOCOL_V3, FREEZE_V3 = "research/forecasts/PROTOCOL_v3.md", "research/forecasts/FREEZE_v3.md"
PANEL_DAYS, FORECAST_SCORES = "panel-days", "forecast-scores"
SECTION_HEADING = re.compile(r"^## Checked by `([a-z-]+)`\s*$", re.MULTILINE)


def section_text(text: str, section: str) -> str:
    """The record's preamble (with the protocol commit line) plus the named section's own text."""
    headings = list(SECTION_HEADING.finditer(text))
    preamble = text[: headings[0].start()] if headings else text
    for i, heading in enumerate(headings):
        if heading.group(1) == section:
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            return preamble + text[heading.start() : end]
    raise NotFrozen(f"the freeze record has no section for {section!r}")


def require_section_frozen(root: Path, commit: str, section: str, protocol_file: str = PROTOCOL_V3,
                           freeze_file: str = FREEZE_V3, git: Git | None = None) -> Freeze:  # fmt: skip
    root = Path(root)
    git = git or Git(root)
    if not (root / freeze_file).is_file():
        raise NotYetFrozen(f"{freeze_file} does not exist: {protocol_file} is not frozen yet")
    freeze = read_version_freeze(section_text((root / freeze_file).read_text(encoding="utf-8"), section), protocol_file)
    recorded = git.first_commit_containing(freeze.protocol_commit, freeze_file)
    if not git.is_ancestor(freeze.protocol_commit, commit) or not recorded or not git.is_ancestor(recorded, commit):
        raise NotFrozen(f"the {protocol_file} freeze is not in the history of {commit[:10]}")
    text = git.committed_text(protocol_file, freeze.protocol_commit)
    if text is None or hashlib.sha256(text.encode("utf-8")).hexdigest() != freeze.hashes[protocol_file]:
        raise NotFrozen(f"{protocol_file} at the protocol commit is not the frozen version")
    changed = changed_files(root, freeze)
    if changed:
        raise NotFrozen(f"{section}'s frozen files changed after the freeze: {', '.join(changed)} (a new version)")
    return freeze
