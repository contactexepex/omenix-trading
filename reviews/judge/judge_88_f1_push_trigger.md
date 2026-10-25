# Judge 88: F1 forecast capture started by the 3 pm push (`story/f1-push-trigger`, before merge)

Date: 14 Oct 2026 (UTC). Branch at 6af481d (draft PR #98). Claims: `reviews/claude/response_67_f1-g5.md` addendum 6.
It must merge before 09:25 UTC on 15 Oct.

## Verdict: PASS, with one should-fix (a test that keeps the gate standard-library only)

**What changed:**
- `forecast-capture.yml` also starts on a push to `main` that touches `research/data/quotes/**/*.canonical`. The
  14:00 IST cron stays as the fallback.
- A new `gate` job runs `python -m fno.pipeline.capture_gate --event <event>` before any install, and the capture job
  runs only if it prints `run=true`.
- The gate says no when today's v2 pack is already on `main` (checked out fresh at `ref: main`). It also says no when
  a **push**-started run begins after 15:13 IST.
- The workflow-level concurrency group (`forecast-capture`, no cancel) runs the workflow's runs one at a time.

**The orchestrator's three probe points:**

| Point | Check | Result |
|---|---|---|
| (a) A push of a quotes CSV alone starts nothing | The trigger's `paths` is only `research/data/quotes/**/*.canonical`, so a CSV-only push does not match. The recorder's normal commit carries the `.canonical` too, so it matches | MET (by the workflow's filter, read; YAML parsed with my own script) |
| (b) Cron and push on the same day | Runs are serialised by the group. The later run's gate checks out the newest `main` and skips once the pack is there. A late cron (today's case) still captures a missed day; a push run after 15:13 skips. Both orders traced, and the gate's tests cover pack-present and late-push. | MET (reasoning plus tests) |
| (c) No frozen file changed | The diff touches `forecast-capture.yml`, a new `fno/pipeline/capture_gate.py`, the claims and a test. `FREEZE_v3.md` pins `fno/pipeline/panel_days.py`, `panel_wiring.py` and `panel-days.yml`, none of which changed. `forecast-capture.yml` is not pinned. The capture, fire and collect steps are unchanged | MET |

**The gate runs before any install, which I tested:** in an empty virtual environment (no third-party packages), the
gate runs and answers.
- At about 18:20 IST a push run gives `run=false` (late).
- A cron run gives `run=true`. Today's pack is missing, so a late cron still records the missed day, as designed.

**My plants (4, `tests/pipeline/test_capture_gate.py`): all caught.**

| Plant | Result |
|---|---|
| Pack check off | 1 failed |
| Late push allowed | 1 failed |
| The late rule applied to every event | 1 failed |
| The boundary moved to `>=` 15:13 | 1 failed |

**Gates (my runs, `python -B`, caches cleared, token unset):**
- full suite: 3,113 passed;
- ruff, format (698 files) and imports (705): clean;
- `git merge-tree` with `main`: clean.

**Should-fix: a test that the gate imports only the standard library.**
- The gate imports `fno.ai.paths` and `fno.models` and runs before `pip install`.
- If a later change makes either import a third-party package, the gate crashes and **every** capture stops,
  including the cron fallback.
- Add a test that runs the gate with `-S` (site packages disabled) or in an empty environment and expects `run=`
  output.

**Accepted limits, as stated:**
- A `.canonical` commit pushed with an Actions token starts nothing; the cron covers it.
- If the cron run is in progress and fails without capturing, a queued push run after 15:13 skips, and the day is
  lost.

**Verdict: PASS** for 6af481d. Merge before 09:25 UTC on 15 Oct. After the merge I check `main` and CI. Tomorrow's 3
pm push is the first live test: I will check that it started the capture.

## Addendum 1 (14 Oct 2026): merge e3639f5 and story/f1-gate-stdlib-test d6d72df

### Merge check: e3639f5 MET

- Parents 82830e0 and 6af481d. My recomputed `git merge-tree` of the two parents equals e3639f5 exactly (empty diff).
- Code changed on `main` since my last check (82830e0 to 875b3ff): only the three files of this story
  (`forecast-capture.yml`, `capture_gate.py`, `test_capture_gate.py`). The later commits are logs and data. No unjudged
  code on `main`.
- CI on the merge: not yet read; I check it with the next merge.

### d6d72df: should-fix "stdlib-only test for the gate"

| Criterion | Result | Evidence |
|---|---|---|
| The gate's real entry point runs with no installed library | MET | New test runs `main(['--event', 'schedule'])` under `python -S -I` with only the repository on `sys.path`; asserts exit 0 and a `run=` line. `main` only reads files and prints, so running it against the real checkout is safe. |
| The check itself proves the libraries are really absent | MET | Second test: `requests`, `yaml`, `numpy`, `google`, `psycopg` and `jsonschema` must fail to import in that mode. Guards against a Python whose packages sit outside site-packages. |
| Catches a third-party import anywhere in the gate's import graph | MET | My 4 plants, each caught (1 failed, 5 passed): `requests` in `capture_gate.py`; `psycopg` in `capture_gate.py`; `numpy` in `fno/models.py` (transitive); `jsonschema` in `fno/ai/paths.py` (transitive). All restored; worktree clean. |
| Gates | MET | Trial merge with `main` 875b3ff: 3,122 passed (Slack token unset); ruff check and format clean; check_imports clean. Test file 71 lines. |
| Scope | MET | One test file changed; no code, no frozen file. |

Claims vs reality: the orchestrator's "two planted imports caught, 3,122 passed" matches my own run.

Follow-up (minor, not blocking): the test imports `main` rather than running `python -m fno.pipeline.capture_gate` as
the workflow does. The difference is only `runpy`, so the risk is small.

**Verdict: PASS** for d6d72df. Merge it into `main`. After the merge I check `main` and CI.
