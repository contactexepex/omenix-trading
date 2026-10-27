"""CF1 step 2: a `git pull ... && git push ...` must never be followed by another command in the same run block.

Under `set -e` a failing command inside an `&&` list does not stop the script, so a failed pull used to let the next
command decide the exit status and the run ended green with nothing pushed (P2d judge 54, F1). The pair is safe as
the LAST command of its block (the list's status is the step's status) and inside a retry loop that ends in `exit
1`. Scans every workflow and every ops/ script."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PAIR = re.compile(r"git pull\b[^\n]*&&[^\n]*git push\b")
# a failed push turned into success
SWALLOWED = re.compile(r"git push\b[^\n]*(\|\|\s*(true|:)(?!\w)|;\s*(exit 0|true)(?!\w))")


def blocks() -> list[tuple[str, str]]:
    found = []
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for job in yaml.safe_load(workflow.read_text()).get("jobs", {}).values():
            found += [
                (f"{workflow.name}:{step.get('name', '')}", step["run"]) for step in job["steps"] if "run" in step
            ]
    found += [(script.name, script.read_text()) for script in sorted((ROOT / "ops").glob("*.sh"))]
    return found


def commands(block: str) -> list[str]:
    """The non-empty, non-comment lines of a run block, with a `\\` continuation joined to the line it continues."""
    joined, pending = [], ""
    for raw in block.splitlines():
        line = raw.strip()
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
            continue
        line, pending = pending + line, ""
        if line and not line.startswith("#"):
            joined.append(line)
    if pending.strip():
        joined.append(pending.strip())
    return joined


def problems(block: str) -> list[str]:
    lines = commands(block)
    bad = []
    for index, line in enumerate(lines):
        if not PAIR.search(line):
            continue
        is_last = index == len(lines) - 1
        retry_loop = line.endswith("&& exit 0") and lines[-1] == "exit 1"
        if SWALLOWED.search(line) or not (is_last or retry_loop):
            bad.append(line)
    return bad


def test_no_workflow_or_script_has_a_pull_and_push_that_a_later_command_can_mask():
    assert [(name, bad) for name, block in blocks() if (bad := problems(block))] == []


def test_the_scan_sees_the_pairs_it_is_meant_to_police():
    """Not vacuous: the repository has pairs (last commands and the two retry loops) and the scan finds them."""
    pairs = [name for name, block in blocks() if PAIR.search(block)]
    assert (
        len(pairs) >= 8
        and any("global-cues" in name for name in pairs)
        and any("vix-history" in name for name in pairs)
    )


def test_the_scan_catches_the_exact_pattern_that_failed_p2d_and_accepts_the_two_safe_shapes():
    masked = 'git add x\ngit pull --no-rebase --no-edit origin main && git push origin HEAD:main\nexit "$broken"\n'
    last = "git add x\ngit pull --no-rebase --no-edit origin main && git push origin HEAD:main\n"
    loop = (
        "for try in 1 2 3; do\n  git pull origin main && git push origin HEAD:main && exit 0\n  sleep 1\ndone\nexit 1\n"
    )
    comment_after = last + "# a comment is not a command\n"
    assert problems(masked) and not problems(last) and not problems(loop) and not problems(comment_after)
    assert problems("git pull a && git push b\necho done\n")


def test_the_scan_also_catches_a_continuation_a_swallowed_failure_and_a_one_line_exit_0():
    """judge 55 F1: three shapes that used to slip past."""
    continued = 'git pull --no-rebase origin main \\\n  && git push origin HEAD:main\nexit "$broken"\n'
    assert problems(continued)
    assert problems("git pull origin main && git push origin HEAD:main || true\n")
    assert problems("git pull origin main && git push origin HEAD:main || :\n")
    assert problems("git pull origin main && git push origin HEAD:main; exit 0\n")
    assert problems("git pull origin main && git push origin HEAD:main; true\n")
    last_continued = "git add x\ngit pull origin main \\\n  && git push origin HEAD:main\n"
    assert not problems(last_continued)  # a continued pair that IS the last command is as safe as one line
