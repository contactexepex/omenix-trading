"""Print the v4 freeze record's generated sections (the freeze plan, response 287; story G6 freeze, criteria 1, 3 and
9): the byte-checked table with each file's SHA-256, the recorded files with their SHA-256 and lock (G11's in their own
table), the files named as not deciding, the platform the freeze ran on, and the disclosure of every back-fill, live
row and report made on or before the freeze day. The freeze commit pastes them into `research/forecasts/FREEZE_v4.md`;
`fno.forecast_scoring.v4.freeze_check.check` then checks the repository against them.

It refuses, printing why and nothing else, on a tree with uncommitted changes ("as of commit" would be false), while a
listed file or pattern matches nothing (it would be left out silently), or while a v4 module still reads the configured
rate (protocol 1.4).

    python tools/v4_freeze_table.py --frozen-on 2026-10-25
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fno.forecast_scoring.v4.freeze_check import rate_readers, recorded, table, unmatched  # noqa: E402
from fno.forecast_scoring.v4.freeze_classes import NOT_DECIDING  # noqa: E402
from fno.forecast_scoring.v4.freeze_disclosure import disclosure  # noqa: E402


def platform_line() -> str:
    """The judge 508 libm limit: a last-bit difference between C libraries can move a replayed value."""
    import numpy

    name, version = platform.libc_ver()
    libc = f"{name}-{version}" if name else "unknown"
    return f"Python {platform.python_version()}, numpy {numpy.__version__}, C library {libc}, {platform.machine()}"


def refusals(root: Path, dirty: str) -> list[str]:
    found = [f"uncommitted changes: {line}" for line in dirty.splitlines() if line.strip()]
    found += [f"matches no file: {p}" for p in unmatched(root)]
    return found + [f"reads the configured rate (protocol 1.4: pricing.py only): {p}" for p in rate_readers(root)]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--frozen-on", type=date.fromisoformat, required=True, help="the record's Frozen on day")
    frozen_on = parser.parse_args().frozen_on
    refused = refusals(ROOT, _git("status", "--porcelain"))
    if refused:
        print("\n".join(["freeze tables NOT printed:", *refused]))
        return 1
    not_deciding = "\n".join(f"- `{path}`: {why}" for path, why in sorted(NOT_DECIDING.items()))
    print(f"## Frozen files (checked byte for byte)\n\n{table(ROOT)}")
    print(f"\n## Recorded, not byte-checked\n\n{recorded(ROOT)}")
    print(f"\n## Reached by v4's code, deciding no v4 value (named, not hashed)\n\n{not_deciding}")
    print(f"\n## Platform\n\n{platform_line()}")
    print(f"\n## Disclosure (protocol section 8), as of commit `{_git('rev-parse', 'HEAD').strip()}`\n")
    print(disclosure(ROOT, frozen_on))
    return 0


if __name__ == "__main__":
    sys.exit(main())
