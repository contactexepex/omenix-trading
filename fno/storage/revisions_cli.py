"""`python -m fno data-revisions`: later NSE versions of archived raw files (story A11).

- `sweep <dataset>` reads each session's file from NSE in full and saves any version that differs from the archived
  one (and from every revision already saved) to Drive's `revisions` area, with an index row; the rows are committed.
- `versions <dataset> --day D [--as-of TIME]` shows the archived versions of one day's file and which one the
  point-in-time reader (at TIME) and the latest reader return, read from Drive and checked against their SHA-256.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from ..models import IST, today_local

STORED = "REVISION {day} {path}: NSE's newer version kept as {revision_path} ({size} bytes, available from {at})"
NOT_ARCHIVED = "not in the raw archive, so not a revision (the librarian archives it): {path}"
UNANSWERED = "no answer: {path}: {reason} (check again next sweep)"
SUMMARY = "revisions sweep: {checked} files read, {stored} new revisions, {unanswered} unanswered"


def add_revisions_parser(subparsers) -> None:
    from .wiring import FINGERPRINT_SOURCES

    rev = subparsers.add_parser("data-revisions", help="later NSE versions of archived raw files (story A11)")
    actions = rev.add_subparsers(dest="revisions_cmd", required=True)
    sweep = actions.add_parser("sweep", help="read NSE's files in full; keep any newer version as a revision")
    sweep.add_argument("dataset", choices=sorted(FINGERPRINT_SOURCES))
    sweep.add_argument("--from", dest="start", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    sweep.add_argument("--to", dest="end", type=date.fromisoformat, default=today_local() - timedelta(days=1))
    versions = actions.add_parser("versions", help="one day's archived versions and which one each reader returns")
    versions.add_argument("dataset", choices=sorted(FINGERPRINT_SOURCES))
    versions.add_argument("--day", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    versions.add_argument("--as-of", type=_ist_time, default=None, help="YYYY-MM-DDTHH:MM (IST unless given)")
    rev.set_defaults(func=cmd_data_revisions)


def _ist_time(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo else moment.replace(tzinfo=IST)


def cmd_data_revisions(args) -> int:
    from . import wiring

    source_type = wiring.FINGERPRINT_SOURCES[args.dataset]
    if args.revisions_cmd == "versions":
        return _versions(source_type, args.day, args.as_of)
    return _sweep(source_type, args.start, args.end)


def _sweep(source_type, start: date | None, end: date) -> int:
    from . import wiring
    from .coverage import archive_range, days_between
    from .revision_source import sweep_revisions

    archive, recorder = wiring.build_revision_archive(), wiring.build_manifest_recorder()
    calendar = wiring.build_session_calendar()
    days = [d for d in days_between(*archive_range(source_type, start, end)) if calendar.is_session(d)]
    try:
        source = wiring.build_revision_capturing_source(source_type, archive)
        result = sweep_revisions(source, [source_type.path_for(d) for d in days])
        no_answer = [UNANSWERED.format(path=p, reason=why) for p, why in result.unanswered.items()]
        stopped = [f"STOPPED: {result.stopped}"] if result.stopped else []
        lines = revision_lines(archive) + no_answer + stopped
        summary = {"checked": result.checked, "stored": len(archive.stored), "unanswered": len(result.unanswered)}
        lines.append(SUMMARY.format(**summary))
        print("\n".join(lines))
    finally:
        print(recorder.commit(f"data-revisions sweep {source_type.dataset}"))
    return 1 if archive.stored or result.unanswered or result.stopped else 0


def revision_lines(archive) -> list[str]:
    """What a pass saved and what it could not compare (shared by every command that captures revisions)."""
    lines = [
        STORED.format(day=r.day, path=r.path, revision_path=r.revision_path, size=r.size_bytes, at=r.available_from)
        for r in archive.stored
    ]
    return lines + [NOT_ARCHIVED.format(path=p) for p in archive.not_archived]


def _versions(source_type, day: date, as_of: datetime | None) -> int:
    from . import wiring

    path, latest = source_type.path_for(day), wiring.build_versioned_reader()
    print(f"raw      {path}")
    for r in latest.index.for_path(path):
        print(f"revision {r.revision_path} available from {r.available_from:%Y-%m-%d %H:%M %Z}")
    readers = [("latest", latest)]
    if as_of is not None:
        readers.append((f"as of {as_of:%Y-%m-%d %H:%M %Z}", wiring.build_versioned_reader(as_of)))
    for label, reader in readers:
        data = reader.get(path)
        sha256 = hashlib.sha256(data).hexdigest() if data is not None else "no file"
        chosen = reader.version(path)
        print(f"{label}: {'raw' if chosen is None else chosen.revision_path} sha256 {sha256}")
    return 0
