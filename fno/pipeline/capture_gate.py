"""Whether a forecast-capture run should go ahead (owner's orchestrator, 14 Oct 2026; response 67 addendum 5). GitHub's
`schedule` was hours late on 14 Oct, so the capture also starts on the push that lands the 3 pm canonical snapshot on
`main`, with the cron kept as a fallback. Every run asks this first, after earlier runs of the same concurrency group
have finished:
- the day's v2 pack is already on `main`: an earlier run captured the day, so this one stops (one capture a day);
- a push-started run after 15:13 IST stops: the capture's own last pull for the snapshot is 15:13 (protocol v2 section
  5), so it could only add late records. The cron run remains the fallback that records a missed day, late.
Standard library only: the gate runs before any install.

python -m fno.pipeline.capture_gate --event <github.event_name>   # prints run=true or run=false and the reason
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from ..ai.paths import pack_path
from ..ai.timing import LATEST_START
from ..models import now_ist

PUSH_EVENT = "push"
LATE_PUSH = "{day}: push after {latest:%H:%M} IST: only late records could follow (the cron run covers a missed day)"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def skip_reason(root: Path, now: datetime, event: str) -> str:
    """Why this run must not capture, or '' when it should."""
    day = now.date()
    if (Path(root) / pack_path(day)).is_file():
        return f"{day}: the day's pack is already on main (captured by an earlier run)"
    if event == PUSH_EVENT and now.time() > LATEST_START:
        return LATE_PUSH.format(day=day, latest=LATEST_START)
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m fno.pipeline.capture_gate")
    parser.add_argument("--event", required=True, help="the GitHub event that started the run")
    reason = skip_reason(REPOSITORY_ROOT, now_ist(), parser.parse_args(argv).event)
    print(f"run={'false' if reason else 'true'}")
    print(f"reason={reason or 'capture due'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
