# Judge 90: F1, no AI fire on a late start: `story/f1-no-late-fire` at 101c449 (response 67 addendum 8)

Standard: `docs/JUDGE.md`. What I checked:
- the full diff (fire, collect, timing, capture_gate, one new test file);
- 5 probes and 5 mutation plants of my own;
- the freeze lists;
- the full gates on a trial merge with `main`.

## Gates

On a trial merge with `main` (80ae31a):
- **3,126 passed**, with `FNO_SLACK_BOT_TOKEN` unset;
- `ruff check` and `ruff format --check` clean;
- `check_imports` clean.

My first full run had 1 failure, `test_capture_gate` at 15:14. I traced it to my own plant method, not the branch:
- My plant changed `LATEST_START` to 15:14 and then restored the file within the same second, at the same size.
- Meanwhile the gate's stdlib test runs `python -S -I` without `-B`, and that subprocess wrote a `.pyc` holding 15:14.
- Python accepted that stale `.pyc`: same size and same mtime second.
- After clearing `__pycache__`, the same tree passes all 3,126.

This is very likely also the single unnamed failure in judge 89 addendum 1, which came right after plants. That is
reasoning, not proven. I narrow that follow-up accordingly: it was a judge-harness artefact, not a project flake. I now
clear `__pycache__` after planting.

## Criteria

| Criterion | Result | Evidence |
|---|---|---|
| After 15:13 IST, `fire` fires no book, writes `fired:false, late_start:true` with a reason, and sends one #fno-desk line | MET | Code; builder tests. My plants were caught: alert removed (2 failed); `late_start` set to false (3 failed). |
| (a) Boundary and timezone | MET | Probes: 15:12:59 fires both books; 15:13:00 fires (builder test); 15:13:00 plus 1 microsecond fires none. A UTC-aware clock at 09:43:00 fires and at 09:43:01 does not: the comparison is between timezone-aware instants. A run after midnight for the previous day is late and fires none. Production clock is `now_ist` (`fno/ai/wiring.py`). My plant `>` -> `>=` was caught; so was `LATEST_START` moved to 15:14. |
| A late run never overwrites an earlier on-time fire | MET | Probe: fire at 14:00, then a run at 19:27 says "already fired"; the log is byte-identical and nothing is fired twice. |
| (b) A late start can never produce a scored record | MET (from code) | The late path fires nothing, so no commitment can come from it. The collector gives `no_submission` with probabilities all None (builder test). `scoring_gate` scores only `on_time` audits (`scoring_gate.py:40`). The only route to a scored record would be a commitment that reached the repository by 15:15:00 from outside this path, for example a manual fire. That would be a real on-time answer, checked by `receipt_deadline` as on any day. |
| (c) Moving the constant changes nothing frozen | MET | None of `fno/ai/timing.py`, `fire.py`, `collect.py` or `capture_gate.py` is listed in `research/forecasts/FREEZE*.md` or in `PROTOCOL.md` `frozen_files`. The value is unchanged (15:13, the same `>` comparison). My plant `>` -> `>=` in `capture_gate` was caught. |
| One source for 15:13 | MET | `capture_gate` imports `LATEST_START`; the old `PUSH_LATEST` is gone. The gate's stdlib-only test still passes: `fno/ai/timing.py` imports only the standard library and `fno.models`. |

## Claims vs reality

- Builder: 3 tests, 2 mutations caught, 3,126 passed. All match my run.
- Addendum 7's account of the 14 Oct late run matches the Actions API: forecast-capture run 1 is a `schedule` run started
  at 13:56:51 UTC.

## Findings

**Should-fix (docs):** the label `no_submission` for a late start contradicts the owner checklist.
- `docs/stories/F1-G5-owner-checklist.md` defines `no_submission` as "the routine ran but never sealed" and sends the
  owner to the session link. A late start has no session.
- Scoring is unaffected: both `no_submission` and `not_fired` are unscored.
- My view (reasoning only): `not_fired` with the reason "late start" is the truer label. It would also remove the special
  case in `collect.py`.
- If `no_submission` stays, add a checklist row for "late start" so the owner does not hunt for a session that does not
  exist.

**Follow-up:** the gate's stdlib test subprocess writes `__pycache__` into the working tree. That is harmless in CI, but
it is how the stale cache above arose.

## Project rules

- No orders placed; no secrets in files.
- The constant is at the module top.
- Files are under 350 lines.
- Composition is unchanged.

## Verdict: PASS for 101c449

Merge it before 09:25 UTC on 15 Oct. After the merge I check `main` and CI.

## Addendum 1 (14 Oct 2026): merge cc5efff MET

- **Merge matches the recomputation.** Parents are 3a24de1 and 101c449. My recomputed `git merge-tree` of the two
  parents equals cc5efff exactly (empty diff).
- **No unjudged code on `main`.** From cc5efff to `main` 89910c5, nothing changed under `fno`, `tests`, `tools`,
  `.github`, `config.yaml`, `db` or `.gitattributes`. The later commits are logs.
- **CI is pending.** CI on cc5efff, fb8bbdb and 89910c5 was still running at 14:57 UTC. I confirm it at my next check.
- **The flaky-test hunt is closed.** Builder A saw no failure in 7 full runs on 14105e8. They also gave the mechanism:
  `python -I` ignores `PYTHONDONTWRITEBYTECODE`, so the gate test's `-S -I` subprocess writes `.pyc` files. That fits
  my diagnosis. My harness now clears `__pycache__` after every restore.

## Addendum 2 (14 Oct 2026): `story/f1-late-start-status` 1eb005c (the should-fix)

| Item | Result | Evidence |
|---|---|---|
| A late start is recorded `not_fired` with reason "late start"; the special case in `collect.py` is gone | MET | `collect.py` is back to blob fe92c58, the version before 101c449: one rule for every unfired book. The note reads "the routine was not fired: late start: ...". My plant (`NOT_FIRED` -> `NO_SUBMISSION`) was caught: 2 failed. |
| Checklist row | MET | The row `not_fired: ... late start` says no session exists and nothing needs fixing. The `no_submission` row again means only "ran but never sealed". |
| Scoring still ignores the late path | MET | `scoring_gate` scores only `on_time` audits, and `not_fired` gives all-None probabilities (test). |
| No frozen file touched | MET | Neither file, nor the checklist, is listed in `research/forecasts/FREEZE*.md` or in `PROTOCOL.md` `frozen_files`. |
| Gates | MET | Trial merge with `main`, with `__pycache__` cleared after the plant: 3,149 passed with the token unset. `ruff check`, `ruff format --check` and `check_imports` are clean. |

**Verdict: PASS** for 1eb005c. Merge it. After the merge I check `main` and CI.

CI on the cc5efff merge (addendum 1): green on cc5efff, fb8bbdb, 89910c5, 70ccd44 and d111ea6.

## Addendum 3 (14 Oct 2026): merge 5226514 MET

- **Merge matches the recomputation.** The parents are b708970 and 1eb005c. My recomputed `git merge-tree` of the two
  parents equals 5226514 exactly (empty diff).
- **No unjudged code reached `main`.** From 5226514 to `main` at a8c71af, nothing changed in code paths. The only other
  commit, 6c2badd, adds filings manifests: 3 data CSVs.
- **CI is green** on a8c71af, the first push carrying the merge, and on 886f572.
