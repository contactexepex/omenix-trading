"""Story SEC1: every package install is hash-locked, and the locks match their inputs.

Offline static checks. The scanner finds every `pip install`, `pip3 install`, `python -m pip install` and `uv pip
install` (also inside multi-line `run: |` blocks and backslash continuations) in `.github/`, `ops/`, the docs, the root
Markdown files and `fno/`, and requires `--require-hashes` with a `.lock` file; installs in workflows also need
`--only-binary`. A lock must hold only exact `==` pins, each with a SHA-256 hash, and must cover every requirement of
its input files at a version the input allows. The plant tests prove the scanner would catch a regression.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parent.parent
INSTALL = re.compile(r"(?:\bpip3?|\bpython3?\s+-m\s+pip|\buv\s+pip)\s+install\b")
LOCK_ARGUMENT = re.compile(r"(?:-r|--requirement)[ =]+\S*\.lock\b")
SHELL_VARIABLE = re.compile(r'^\s*(\w+)="([^"]*)"', re.MULTILINE)
CACHE_PATH = re.compile(r"cache-dependency-path:\s*(\S+)")
# lock file -> the input files it is made from (ops/relock.sh)
LOCKS = {
    "requirements.lock": ("requirements.txt",),
    "requirements-groww.lock": ("requirements.txt", "requirements-groww.txt"),
    "requirements-oauth.lock": ("requirements-oauth.txt",),
}
SCANNED_SUFFIXES = {".yml", ".yaml", ".sh", ".py", ".md"}


def scanned_files() -> list[Path]:
    """Files that may tell a person or a job to install packages (not stories, reviews, logs or tests, which quote
    history)."""
    roots = [ROOT / ".github", ROOT / "ops", ROOT / "docs", ROOT / "fno"]
    files = [p for r in roots for p in r.rglob("*") if p.is_file() and p.suffix in SCANNED_SUFFIXES]
    files += [p for p in ROOT.glob("*.md")]
    return sorted(p for p in files if "docs/stories" not in p.as_posix() and "__pycache__" not in p.parts)


def logical_lines(text: str) -> list[str]:
    """Lines with backslash continuations joined, so flags on a continued line belong to their command."""
    return re.sub(r"\\\n\s*", " ", text).splitlines()


def variants(line: str, text: str) -> list[str]:
    """The line with each shell variable it names replaced by every value the file assigns to it (so
    `$requirements` is checked as each flavour); the line itself when it names no assigned variable."""
    assigned: dict[str, list[str]] = {}
    for name, value in SHELL_VARIABLE.findall(text):
        assigned.setdefault(name, []).append(value)
    found = [name for name in assigned if re.search(rf"\$\{{?{name}\b", line)]
    if not found:
        return [line]
    out = [line]
    for name in found:
        out = [re.sub(rf"\$\{{?{name}\}}?", value, text_line) for text_line in out for value in assigned[name]]
    return out


def install_problems(path: str, text: str, need_binary: bool) -> list[str]:
    problems = []
    for line in logical_lines(text):
        if not INSTALL.search(line):
            continue
        for checked in variants(line, text):
            tail = checked[INSTALL.search(checked).start() :]
            if "--require-hashes" not in tail or not LOCK_ARGUMENT.search(tail):
                problems.append(f"{path}: install without --require-hashes and a .lock file: {line.strip()}")
            elif need_binary and "--only-binary" not in tail:
                problems.append(f"{path}: workflow install without --only-binary: {line.strip()}")
    return problems


def cache_problems(path: str, text: str) -> list[str]:
    return [f"{path}: cache-dependency-path is not a lock file: {v}" for v in CACHE_PATH.findall(text)
            if not v.strip("\"'").endswith(".lock")]  # fmt: skip


def scan(files: list[Path]) -> list[str]:
    problems = []
    for file in files:
        name = file.relative_to(ROOT).as_posix()
        text = file.read_text(encoding="utf-8")
        problems += install_problems(name, text, need_binary=name.startswith(".github/"))
        problems += cache_problems(name, text)
    return problems


ENTRY = re.compile(r"^(?P<name>[A-Za-z0-9_.\-]+)(?P<op>[=<>!~]+)(?P<version>[^\s;\\]+)")


def lock_entries(text: str) -> dict[str, tuple[str, int]]:
    """Canonical name -> (version, hash count); raises AssertionError for anything but an exact hashed pin."""
    entries: dict[str, tuple[str, int]] = {}
    blocks = re.split(r"\n(?=[A-Za-z0-9])", "\n".join(ln for ln in text.splitlines() if not ln.startswith("#")))
    for block in (b for b in blocks if b.strip()):
        found = ENTRY.match(block.strip())
        assert found and found["op"] == "==", f"not an exact pin: {block.splitlines()[0]!r}"
        hashes = len(re.findall(r"--hash=sha256:[0-9a-f]{64}", block))
        assert hashes, f"no hash for {found['name']}"
        entries[canonicalize_name(found["name"])] = (found["version"], hashes)
    return entries


def input_requirements(text: str) -> list[Requirement]:
    lines = (line.split("#", 1)[0].strip() for line in text.splitlines())
    return [Requirement(line) for line in lines if line and not line.startswith("-")]


def coverage_problems(lock: str, inputs: dict[str, str]) -> list[str]:
    """Every input requirement must have a pin in the lock at a version its specifier allows."""
    pins = lock_entries(lock)
    problems = []
    for file, text in inputs.items():
        for requirement in input_requirements(text):
            pin = pins.get(canonicalize_name(requirement.name))
            if pin is None:
                problems.append(f"{file}: {requirement.name} has no pin in the lock (run ops/relock.sh)")
            elif not requirement.specifier.contains(pin[0], prereleases=True):
                problems.append(f"{file}: pin {requirement.name}=={pin[0]} breaks {requirement.specifier}")
    return problems


# ---- the repository itself -------------------------------------------------------------------------------------


def test_every_install_in_the_repository_is_hash_locked():
    files = scanned_files()
    assert len(files) > 20  # the walk found the workflows, ops scripts and docs
    assert scan(files) == []


def test_all_fourteen_workflow_installs_are_present_and_locked():
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    installs = [line for w in workflows for line in logical_lines(w.read_text("utf-8")) if INSTALL.search(line)]
    assert len(installs) == 14 and all("requirements.lock" in line for line in installs)


@pytest.mark.parametrize("lock", sorted(LOCKS))
def test_each_lock_has_only_exact_hashed_pins_and_covers_its_inputs(lock):
    entries = lock_entries((ROOT / lock).read_text("utf-8"))
    assert entries
    inputs = {name: (ROOT / name).read_text("utf-8") for name in LOCKS[lock]}
    assert coverage_problems((ROOT / lock).read_text("utf-8"), inputs) == []


# ---- plants: each regression must be caught --------------------------------------------------------------------

LOCKED = "pip install --require-hashes --only-binary=:all: -r requirements.lock"


def test_plant_a_plain_install_in_a_run_block_is_caught():
    text = f"steps:\n  - run: |\n      echo hi\n      python -m pip install foo\n  - run: {LOCKED}\n"
    assert len(install_problems(".github/workflows/x.yml", text, need_binary=True)) == 1


@pytest.mark.parametrize(
    "command", ["pip3 install x", "uv pip install x", "python3 -m pip install -r requirements.txt"]
)
def test_plant_other_pip_spellings_are_caught(command):
    assert install_problems("ops/x.sh", f"#!/bin/sh\n{command}\n", need_binary=False)


def test_plant_hashes_without_a_lock_file_and_a_lock_without_hashes_flag_are_caught():
    assert install_problems("ops/x.sh", "pip install --require-hashes -r requirements.txt\n", need_binary=False)
    assert install_problems("ops/x.sh", "pip install -r requirements.lock\n", need_binary=False)


def test_plant_a_workflow_install_without_only_binary_is_caught_but_not_in_ops():
    line = "pip install --require-hashes -r requirements.lock"
    assert install_problems(".github/workflows/x.yml", line, need_binary=True)
    assert install_problems("ops/x.sh", line, need_binary=False) == []


def test_plant_a_continued_line_keeps_its_flags_with_its_command():
    text = "pip install \\\n  --require-hashes \\\n  -r requirements.lock\n"
    assert install_problems("ops/x.sh", text, need_binary=False) == []


def test_plant_a_shell_variable_is_checked_in_every_flavour():
    good = 'r="--require-hashes -r a.lock"\nr="--require-hashes -r b.lock"\npython -m pip install -q $r\n'
    bad = good.replace('r="--require-hashes -r b.lock"', 'r="-r b.txt"')
    assert install_problems("ops/x.sh", good, need_binary=False) == []
    assert install_problems("ops/x.sh", bad, need_binary=False)


def test_plant_a_cache_path_that_is_not_a_lock_is_caught():
    assert cache_problems("w.yml", "cache-dependency-path: requirements.txt\n")
    assert cache_problems("w.yml", "cache-dependency-path: requirements.lock\n") == []


def test_plant_a_requirement_without_a_lock_pin_and_a_pin_outside_its_range_are_caught():
    lock = "requests==2.34.2 \\\n    --hash=sha256:" + "a" * 64 + "\n"
    assert coverage_problems(lock, {"requirements.txt": "requests>=2.31\n"}) == []
    assert coverage_problems(lock, {"requirements.txt": "requests>=2.31\nnewpkg>=1\n"})
    assert coverage_problems(lock, {"requirements.txt": "requests<2\n"})


def test_plant_a_lock_with_a_range_or_without_a_hash_is_refused():
    with pytest.raises(AssertionError):
        lock_entries("requests>=2.31 \\\n    --hash=sha256:" + "a" * 64 + "\n")
    with pytest.raises(AssertionError):
        lock_entries("requests==2.34.2\n")
