"""Re-runs the plants behind docs/RECORD_CONTRACT.md (story P5).

For every claim in `contract_plants.json`, its tests must pass and, with the claim's plant applied to the source, at
least one of them must fail. A claim in EXPECT_SURVIVE is one the document calls "stated only": its plant is
EXPECTED to go unnoticed, and the tool says so if a test starts catching it (then the document's row should be
upgraded).

    python tools/contract_plants.py            # every claim
    python tools/contract_plants.py W1 G3      # some claims

Safety: it edits a source file for the length of one test run and restores it in a `finally`; it refuses to start
when the file it would edit has uncommitted changes. Exit 1 when a claim's tests fail without the plant, when a
plant goes unnoticed, or when an EXPECT_SURVIVE plant is caught."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAIMS = json.loads((Path(__file__).with_suffix(".json")).read_text())
EXPECT_SURVIVE: tuple[str, ...] = ()  # the "stated only" rows of the contract (none since P5b)


def run_tests(tests: list[str]) -> bool:
    """True when every test passes. `data` tests are included; no bytecode is written, so a plant of equal length
    cannot hide behind a stale .pyc."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    command = [sys.executable, "-m", "pytest", "-q", "-x", "-m", "data or not data", *tests]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=env).returncode == 0


def dirty(path: str) -> bool:
    status = subprocess.run(["git", "status", "--porcelain", "--", path], cwd=ROOT, capture_output=True, text=True)
    return bool(status.stdout.strip())


def check(claim: dict) -> str:
    """'ok' or the problem, for one claim."""
    file = ROOT / claim["file"]
    original = file.read_text()
    if claim["old"] not in original:
        return "plant text not found: the code changed; update the plant"
    if dirty(claim["file"]):
        return f"{claim['file']} has uncommitted changes: commit or stash first"
    if not run_tests(claim["tests"]):
        return "its tests fail without the plant"
    try:
        file.write_text(original.replace(claim["old"], claim["new"], 1))
        caught = not run_tests(claim["tests"])
    finally:
        file.write_text(original)
    if claim["id"] in EXPECT_SURVIVE:
        return "now CAUGHT by a test: upgrade the document's row" if caught else "ok"
    return "ok" if caught else "the plant went unnoticed: the claim is no longer pinned"


def main(argv: list[str]) -> int:
    failures = 0
    for claim in CLAIMS:
        if argv and claim["id"] not in argv:
            continue
        result = check(claim)
        failures += result != "ok"
        print(f"{claim['id']}: {result}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
