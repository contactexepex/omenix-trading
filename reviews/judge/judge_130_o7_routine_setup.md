# Judge 130: O7 one setup script for every scheduled routine: `story/O7-routine-setup` f1ac398 (lane 1)

**What I did:**
- read the whole diff against current `main`: 7 files, `tools/routine_setup.sh`, two tests, the story, CLAUDE.md,
  README and `requirements-groww.txt`;
- ran the script for real;
- ran it with a planted `python` that cannot see the packages, and with a virtual environment first on PATH;
- ran the full gates on a trial merge.

## Gates

On a trial merge with current `origin/main` (clean): **5118 passed**; ruff and `check_imports` are clean.

## Criteria

| Criterion | Status | Evidence |
|---|---|---|
| Installs with the same interpreter it checks | MET | `"$py" -m pip install -q --use-pep517` for every distinct real interpreter behind `python3` and `python`. No bare `pip` appears; the test enforces it |
| Both names import the packages, fail fast in one line | MET | Real run: `routine setup ok: /usr/bin/python3.13 (3s, 16:07:18 IST)`. Planted `python` without site-packages: `routine setup FAILED: 'python' (...) cannot import numpy, requests, yaml`, exit 1 |
| `--groww` adds `growwapi` | MET | `growwapi` is the module `fno/providers/groww.py` imports |
| Hook on | MET | `git config core.hooksPath .githooks`; the hook uses `python3` first, which the script covers |
| Root cause addressed | MET (reasoning, matches the 15 Oct log) | The 15 Oct failure was bare `pip` filling 3.13 while `python` was 3.11. The script installs per interpreter and proves the import, so a mismatch now costs seconds, not 14 minutes, and is never silent |

## The question asked: does the change to `test_groww_install_command.py` weaken it? Partly, yes.

The old test guaranteed that **CLAUDE.md and README.md each held an install command carrying `--use-pep517`**.
The new tests guarantee the script carries the flag and that CLAUDE.md, AGENTS.md and README.md name no **bare**
`pip install`. Nothing now requires CLAUDE.md (the routine's own instructions) to **name the script at all**. If
step 1 were deleted or reworded, every test would still pass and a routine could skip setup. That is a lost
guarantee.

## Must-fix

1. Add one assertion that CLAUDE.md's 3 pm recorder section, and README.md, contain `sh tools/routine_setup.sh
   --groww`. That restores the old guarantee in its new form, and it is a one-line test.

## Follow-ups (not blocking)

- **Virtual environments:** `os.path.realpath(sys.executable)` resolves a venv's `python` to its base interpreter. In
  a venv the script installs into the base and then, correctly, fails the import check. I reproduced this. It fails
  loudly, so it is safe, but it can never succeed in a venv. Install with the name's own `sys.executable`, and use the
  real path only to skip duplicates. Routines don't use venvs today.
- `real=$("$path" -c ...)` under `set -e` aborts without the one-line message if an interpreter cannot start. Wrap it
  like the other steps.
- The pip "running as root" warning prints on every run. That is harmless; `--root-user-action=ignore` would
  silence it.
- After the merge, the routine prompts (scheduled tasks, outside the repository) must call the script, as the story
  says. I will check one routine's next run log.

**Verdict: FAIL for f1ac398d99694676f2b523426b6c35cb25c07708**, on must-fix 1 only (a one-line test). The script
itself is sound and does what the story claims; I verified it by running it.

## Addendum 1 (15 Oct 2026): 0eea4f53847b4f1f6e29f3565dd84abfdc494fa8 (f1ac398..0eea4f5)

| Item | Status | Evidence |
|---|---|---|
| Must-fix 1 | MET | `test_the_3pm_routine_and_readme_name_the_script` checks that CLAUDE.md's "## 3 pm quote recorder" section and README.md contain `sh tools/routine_setup.sh --groww`. The old guarantee is back, in its new form. It passes on the trial merge, where CLAUDE.md auto-merged with main's newer copy |
| Follow-up: virtual environments | Done | The script now installs through each name's own `sys.executable` and uses the real path only to skip duplicates. My run with a fresh venv first on PATH: `routine setup ok: .../venv2/bin/python3 (15s)`. A plain run: `routine setup ok: /usr/bin/python3 (5s)` |
| Follow-up: probe failure | Done | It prints one line: "'<name>' (<path>) does not run", then exits 1 |
| Follow-up: root warning | Done | `--root-user-action=ignore` |

**Gates:** trial merge with current `origin/main` (clean; CLAUDE.md auto-merged): **5203 passed**; ruff and
`check_imports` are clean.

**Remaining edge (not blocking):** de-duplicating by real path treats a venv's `python3` and a base `python` as one
interpreter. If PATH mixes the two, only the first gets the packages, and the import check then fails loudly for
the other. So the edge is safe, never silent. Paths with spaces would also split wrongly. Neither occurs in the
routines' containers.

**Verdict: PASS for 0eea4f53847b4f1f6e29f3565dd84abfdc494fa8.** After the merge: every routine's prompt must call
the script. I will check the next 3 pm recorder run's log for the "routine setup ok" line and its time.
