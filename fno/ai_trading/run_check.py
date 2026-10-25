"""F1t's check of a decided run before it is committed (story F1t criterion 7): one run of the book's day, under its
folder and its write paths, unedited since written, every record a valid D3 record carrying the pointer's book,
pack hashes, the model reported, the fire log's session, the judge's verdict file and the decision version in
`served`. Under a blocking verdict no record may be a chosen trade (criterion 16), and every chosen trade names its
strategy's status (criterion 17b). Any problem means the run is never committed and the book-day is `refused`."""

from __future__ import annotations

import json
from pathlib import Path

from ..constants import Decision, PlaybookStatus
from ..playbook.decision_record import RecordError, validate_record
from ..playbook.decision_store import INPUTS_FILE, SUMS_FILE, DecisionStore
from .ports import SERVED_VERSION, AcceptedDecision, DecidedRun
from .write_snapshot import is_under

PASSED, NOT_YET_PASSED = "strategy passed", "strategy not yet passed"


def run_problems(
    root: Path, decided: DecidedRun, accepted: AcceptedDecision, write_paths: tuple[str, ...]
) -> list[str]:
    store = DecisionStore(root, accepted.book)
    runs = [run for run in store.every_run() if run.parent == store.day_folder(accepted.day)]  # how many, not which
    if not decided.run.is_dir() or decided.run.resolve() not in [r.resolve() for r in runs]:
        return [f"{decided.run} is not a run of {accepted.book} on {accepted.day}"]
    problems = [] if len(runs) == 1 else [f"{len(runs)} runs of {accepted.book} on {accepted.day}: only one may exist"]
    outside = [str(p) for p in (decided.run, *decided.files) if not is_under(root, p, write_paths)]
    problems += [f"written outside the version's write paths: {', '.join(outside)}"] if outside else []
    edited = DecisionStore.edited(decided.run)
    problems += [f"files changed after the run was written: {', '.join(edited)}"] if edited else []
    for record in _records(decided.run):
        content = json.loads(record.read_text("utf-8"))
        problems += [f"{record.name}: {p}" for p in record_problems(content, accepted)]
        if content.get("run_id") != decided.run.name:
            problems.append(
                f"{record.name}: run_id is {content.get('run_id')!r}, not the run folder {decided.run.name!r}"
            )
    return problems


def strategy_label(run: Path) -> str:
    """The run's strategy label (owner, 25 Oct): "" with no chosen trade; else whether every traded strategy passed."""
    statuses = [r["served"]["strategy_status"] for r in map(_read, _records(run)) if _chosen(r)]
    if not statuses:
        return ""
    return PASSED if all(s == PlaybookStatus.PAPER for s in statuses) else NOT_YET_PASSED


def record_problems(record: dict, accepted: AcceptedDecision) -> list[str]:
    try:
        validate_record(record)
    except RecordError as wrong:
        return [str(wrong)]
    expected = {"book": accepted.book, "common_pack_sha256": accepted.common_pack.sha256,
                "private_pack_sha256": accepted.private_pack.sha256, "model_served": accepted.model_reported,
                "session_id": accepted.session}  # fmt: skip
    problems = [
        f"{key} is {record.get(key)!r}, not {value!r}" for key, value in expected.items() if record.get(key) != value
    ]
    if record["served"].get(SERVED_VERSION) != accepted.version:
        problems.append(f"served.{SERVED_VERSION} is not the decision version {accepted.version!r}")
    if (record.get("judge") or "") != accepted.judge:
        problems.append(f"judge is {record.get('judge')!r}, not the verdict file {accepted.judge!r}")
    if _chosen(record) and accepted.judge_blocks:
        problems.append("a chosen trade under a blocking judge verdict (only no-trade and shadow records may exist)")
    status = record["served"].get("strategy_status")
    if _chosen(record) and not (isinstance(status, str) and status.strip()):
        problems.append("a chosen trade without served.strategy_status (the strategy label needs it)")
    return problems


def _chosen(record: dict) -> bool:
    """A record of a trade the book chose (D3: `decision.outcome` "chosen"; a shadow record is never one)."""
    decision = record.get("decision")
    return isinstance(decision, dict) and decision.get("outcome") == Decision.CHOSEN


def _records(run: Path) -> list[Path]:
    return sorted(p for p in Path(run).glob("*.json") if p.name not in (INPUTS_FILE, SUMS_FILE))


def _read(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))
