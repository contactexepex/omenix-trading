"""Public-record safety scan (story O5): refuses files that hold credentials, personal data or broker identifiers.

    python tools/check_records.py            # every tracked file: records (outside fno/, tests/, tools/) get every
                                             # pattern, code gets the credential-shaped ones
    python tools/check_records.py --staged   # only the files staged for the next commit (the git hook runs this)
    python tools/check_records.py PATH ...   # named files or folders, e.g. a session export before it is sent
    --alert                                  # when something is found, also post the lines to #fno-desk

Prints one line per finding (file, line and kind of value, never the value) and exits 1 when anything is found.
Every session turns the same check on as a git pre-commit hook: `git config core.hooksPath .githooks`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fno.record_scan.record_files import NamedFiles, RecordSource, StagedRecords, TrackedRecords  # noqa: E402
from fno.record_scan.wiring import build_record_scanner, send_alert  # noqa: E402

REFUSED = "record scan: REFUSED, {count} finding(s); do not commit or send these files (values are not shown)"
CLEAN = "record scan: clean ({files} files)"
ALERT = (
    "Public-record scan refused a commit in {repository} ({count} finding(s); values are not shown). "
    "Remove the values, then commit again; never bypass the scan.\n{lines}"
)


def source_for(args: argparse.Namespace) -> RecordSource:
    if args.paths:
        return NamedFiles([Path(p) for p in args.paths])
    return StagedRecords(args.root) if args.staged else TrackedRecords(args.root)


def main(argv: list[str] | None = None, alerts=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--staged", action="store_true", help="scan only the files staged for the next commit")
    parser.add_argument("--root", type=Path, default=ROOT, help="the git repository to scan (default: this one)")
    parser.add_argument("--alert", action="store_true", help="post the finding lines to #fno-desk when refused")
    parser.add_argument("paths", nargs="*", help="files or folders to scan instead of the repository")
    args = parser.parse_args(argv)
    records = list(source_for(args).records())
    findings = build_record_scanner().scan(records)
    lines = [str(finding) for finding in findings]
    for line in lines:
        print(line)
    if not findings:
        print(CLEAN.format(files=len(records)))
        return 0
    print(REFUSED.format(count=len(findings)))
    if args.alert:
        text = ALERT.format(repository=args.root.resolve().name, count=len(lines), lines="\n".join(lines))
        print(send_alert(text, alerts))
    return 1


if __name__ == "__main__":
    sys.exit(main())
