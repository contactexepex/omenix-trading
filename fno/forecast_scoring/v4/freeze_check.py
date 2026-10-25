"""Protocol v4's freeze check (protocol section 10; the freeze plan, response 287; story G6 freeze): the tables the
freeze record `research/forecasts/FREEZE_v4.md` carries, made from `freeze_classes`, and every way the repository has
moved since. One place for the lists, so the record's tables and the check cannot disagree."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ...research_engine.ledger import Git
from ...weather.wiring import METHOD_FILES as M1_METHOD_FILES
from .freeze_classes import BYTE_CHECKED_GLOBS, PROTOCOL, RECORDED

ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", re.MULTILINE)
RECORDED_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \| [^|\n]+ \|$", re.MULTILINE)
PROTOCOL_COMMIT = re.compile(r"^Protocol commit: `([0-9a-f]{40})`\s*$", re.MULTILINE)
CONFIG_RATE = re.compile(r"""\[\s*["']risk_free_rate["']\s*\]|get\(\s*["']risk_free_rate["']|build_atm_iv30\(""")
AI_REGISTRATION = "fno/ai/"  # G11's shared files, hashed in their own table (owner, 21 Oct 2026 (3); judge 597.1 m2)
INTACT, NOT_CHECKED, BROKEN = "v4 freeze: intact", "v4 freeze NOT CHECKED: {why}", "v4 freeze BROKEN: {problems}"
DRIFT = "recorded file changed since the freeze: {path} ({reason})"
BYTE_HEADING, RECORDED_HEADING = "## Frozen files (checked byte for byte)", "## Recorded, not byte-checked"


@dataclass(frozen=True)
class FreezeCheck:
    """What the check found: `problems` break the freeze; `not_checked` says why it could not run (a shallow clone);
    `drift` names the recorded files changed since (seen, not a break). The default is the state before any record."""

    problems: tuple[str, ...] = ()
    not_checked: str = ""
    drift: tuple[str, ...] = ()

    def holds(self) -> bool:
        return not self.problems and not self.not_checked

    def lines(self) -> list[str]:
        if self.not_checked:
            head = NOT_CHECKED.format(why=self.not_checked)
        else:
            head = BROKEN.format(problems="; ".join(self.problems)) if self.problems else INTACT
        return [head, *self.drift]


def byte_checked(root: Path) -> list[str]:
    """Every byte-checked path that exists today, M1's method files (V6's rules slot, decision 70) included."""
    found = {p.relative_to(root).as_posix() for pattern in BYTE_CHECKED_GLOBS for p in root.glob(pattern)}
    found |= {f"fno/{name}" for name in M1_METHOD_FILES if (root / "fno" / name).is_file()}
    return sorted(p for p in found if "__pycache__" not in p)


def unmatched(root: Path) -> list[str]:
    """Byte-checked patterns and recorded paths that match no file: a table printed now would leave them out."""
    return [p for p in BYTE_CHECKED_GLOBS if not any(root.glob(p))] + [p for p in RECORDED if not (root / p).is_file()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(root: Path) -> str:
    """The record's table: one row per byte-checked file with its SHA-256."""
    rows = [f"| `{path}` | `{sha256(root / path)}` |" for path in byte_checked(root)]
    return "\n".join(["| File | SHA-256 |", "|---|---|", *rows])


def recorded(root: Path) -> str:
    """The record's recorded files with their SHA-256 and lock; G11's shared AI files in their own table."""
    head = ["| File | SHA-256 | What it decides; its lock |", "|---|---|---|"]
    rows = {p: f"| `{p}` | `{sha256(root / p)}` | {RECORDED[p]} |" for p in sorted(RECORDED) if (root / p).is_file()}
    ai = [row for p, row in rows.items() if p.startswith(AI_REGISTRATION)]
    rest = [row for p, row in rows.items() if not p.startswith(AI_REGISTRATION)]
    return "\n".join([*head, *rest, "", "### AI registration (G11's shared files)", "", *head, *ai])


def section(record: str, heading: str) -> str:
    """The record's part under `heading`, up to the next top-level heading: the disclosure's tables have the same row
    shape as the byte-checked table and must never be read as pins. A bare table (no heading) is read whole."""
    start = record.find(heading)
    if start < 0:
        return record
    end = record.find("\n## ", start + len(heading))
    return record[start : end if end >= 0 else len(record)]


def problems(root: Path, record: str) -> list[str]:
    """Every difference between the record's byte-checked table and the repository: a file changed or gone, and a file
    now in a byte-checked folder that the record does not list (a new rule added after the freeze). Empty: intact."""
    pinned = dict(ROW.findall(section(record, BYTE_HEADING)))
    found = []
    for path, digest in sorted(pinned.items()):
        if not (root / path).is_file():
            found.append(f"{path}: gone since the freeze")
        elif sha256(root / path) != digest:
            found.append(f"{path}: changed since the freeze (a change is a new version, never an edit)")
    found += [f"{path}: added after the freeze" for path in byte_checked(root) if path not in pinned]
    return found


def drift(root: Path, record: str) -> list[str]:
    """The recorded files whose bytes differ from the record's (or are gone): printed on every report, never a break."""
    pinned = dict(RECORDED_ROW.findall(section(record, RECORDED_HEADING)))
    changed = [p for p, d in sorted(pinned.items()) if not (root / p).is_file() or sha256(root / p) != d]
    return [DRIFT.format(path=p, reason=RECORDED.get(p, "no longer recorded")) for p in changed]


def protocol_problems(record: str, git: Git) -> list[str]:
    """The record names one protocol commit; it is in this history, it is the last commit that changed the protocol
    ("the commit that adds this text in its final form", section 10), and the text there is the one the record pins."""
    found = PROTOCOL_COMMIT.findall(record)
    if len(found) != 1:
        return [f"the record has {len(found)} 'Protocol commit: `<40-hex sha>`' lines, not one"]
    commit = found[0]
    if not git.commit_exists(commit) or not git.is_ancestor(commit, git.head()):
        return [f"protocol commit {commit[:10]} is not in this history"]
    touching = git.commits_touching(PROTOCOL)
    if not touching or touching[-1] != commit:
        return [f"protocol commit {commit[:10]} is not the last commit that changed {PROTOCOL}"]
    text = git.committed_text(PROTOCOL, commit)
    pinned = dict(ROW.findall(section(record, BYTE_HEADING))).get(PROTOCOL)
    if text is None or hashlib.sha256(text.encode("utf-8")).hexdigest() != pinned:
        return [f"{PROTOCOL} at the protocol commit {commit[:10]} is not the text the record pins"]
    return []


def check(root: Path, record: str, git: Git) -> FreezeCheck:
    """The whole check on this tree; a shallow clone cannot see the protocol commit, so it is not checked, never
    called broken or intact."""
    if git.is_shallow():
        return FreezeCheck(not_checked="shallow clone: run git fetch --unshallow origin main, then check again")
    found = problems(root, record) + protocol_problems(record, git)
    return FreezeCheck(problems=tuple(found), drift=tuple(drift(root, record)))


def rate_readers(root: Path) -> list[str]:
    """Byte-checked and recorded modules that read `config.yaml`'s `risk_free_rate` or call `build_atm_iv30` (which
    does): v4's rate is `fno/forecast_v4/pricing.V4_RISK_FREE_RATE` only (protocol 1.4; judge 597 SF2)."""
    files = [p for p in byte_checked(root) + sorted(RECORDED) if p.endswith(".py") and (root / p).is_file()]
    return [p for p in files if CONFIG_RATE.search((root / p).read_text(encoding="utf-8"))]
