# Judge 157: the back-fill test reads decompressed records (`story/x-backfill-test-decompressed` 40c6a3f5b48bffb1dcc246f75aac4af739b25cb1), and an after-the-fact lane-1 check of two lane-2 merges (judge A)

**Number note.** The orchestrator asked for 156, but `judge_156_g9_miss_rule_independent.md` already holds it, so this is 157.

## 1. `tests/forecast/test_backfill.py:44`, 40c6a3f5

**The change.**
- `records_gzip(fresh) == committed bytes` becomes `gzip.decompress(records_gzip(fresh)) == gzip.decompress(committed
  bytes)`, with a one-line "why".
- A WORK_REGISTER row (step 7 of noise-and-fairness). It covers this one test only; no other row covers it.

**Checks.**
- **What the protocol requires.** Protocol v3 section 2 asks that the back-fill be "checked against the panel it was
  built from: its own days, and its `pack_sha256` equal to the manifest's SHA-256 at the commit that wrote it".
  - That is the records' content and their pack hash.
  - It is not the gzip byte stream, which depends on the zlib version.
  - The pack-hash check is a separate, unchanged test (`backfill_pack_sha256`, lines 29-32 and 50-52).
  - So the protocol's contract is unchanged, and the test no longer fails for a reason that is not a change: a
    different zlib (the CI now runs Python 3.13).
- **Strength.** Every byte of the CSV still has to match. The builder's proofs fit: a +0.001 change fails, and a level-1
  recompression passes.
- **The file is in no freeze.** `tests/forecast/test_backfill.py` is named in PROTOCOL_v3 as the check, but no FREEZE
  record pins it (searched FREEZE.md, FREEZE_v2, FREEZE_v3 and the freeze tests).
- **Gates on a trial merge with main.** `tests/forecast` plus `tests/test_freeze_sections.py`: **91 passed**. Ruff is
  clean.

**Verdict: PASS for 40c6a3f5b48bffb1dcc246f75aac4af739b25cb1.**

## 2. After the fact: `docs/a16-owner-checklist`, merged 73b488a as lane 2

**Lane.** This is lane 1. JUDGE.md refinement 1 puts schedules there, and this file sets one (`CRON_TZ=Asia/Kolkata 52
8-14 * * *`) and gives the routine's prompt. That it is "only docs" does not decide the lane.

**Content (`docs/stories/A16-owner-checklist.md`, 94 lines):**
- **The schedule covers every mark with overlap.**
  - Seven fires, 08:52-14:52. Each fire at H:52 runs to (H+2):05, and the last one to 15:35.
  - So all 26 marks from 09:15 to 15:30 are covered, and every hour boundary has two runs. That is the A16 design, with
    `tests/intraday/test_two_clones.py` for two writers.
  - "Every day" follows A7, as the 3 pm routine does. The cost is stated: 14 empty short runs a week.
- **Settings:** names only, no values, the same names as the 3 pm environment.
- **The routine prompt:**
  - set-up through `tools/routine_setup.sh --groww` (O7);
  - commit only the recorder's own paths, never `--no-verify`;
  - post to Slack only on "alert NOT sent".

  All three are consistent with CLAUDE.md and A16e.
- **It changes no code** and creates no schedule: the owner creates it.

**Note (real path, unverified, one line).** The 14:52 fire signs in to Groww with the same key while the 3 pm recorder
(started 14:33, capturing until 15:10) is running. Nothing in the repository says whether a new TOTP sign-in ends the
other session's token. During the 5-session trial, also report the 3 pm recorder's result on each of those days, so a
clash shows at once.

**Verdict: PASS (after the fact)**, with the lane recorded as 1.

## 3. After the fact: c7910516 (`story/ci-green-tests`), merged as lane 2

**Lane.** This is lane 1. It edits two existing tests, and JUDGE.md keeps lane 2 for new tests only.

**Content.**
- **`tests/evaluation/test_order_runs.py`.** The test's own `git commit` gets `-c user.name=t -c user.email=t@t` (CI has
  no git identity), through the shared `tests.playbook.builders.git` helper. The assertion is unchanged, so it is not
  loosened.
- **`tests/intraday_backfill/test_read_only.py`.** The verifier test patches `INTRADAY_FOLDER` and `MANIFEST_FOLDER` to
  temporary folders. Before, it read `main`'s real A16b back-fill rows once they existed, a real path after A16b's rule
  8. The assertion is unchanged, and the test is now isolated as it was meant to be.
- **CI.** Green on c791051 (run 38743169675) and on every main run since.

**Verdict: PASS (after the fact)**, with the lane recorded as 1.

## Register check (owner's coordination rule)

None of the three duplicates or contradicts another session's work:
- the back-fill test belongs to G3's own file, and the register row is the builder's;
- the A16 checklist is the A16 builder's, matching the register's "A16 routine (O)" row;
- c7910516 fixes tests owned by D3b and A16b, with no competing change in flight.

## Addendum 1 (15 Oct 2026): `docs/a16-checklist-signin` 3cef31e35e1be3ee6fca1243f4aac95bb4c3d40a (A16 owner checklist, lane 1)

**The change.** One bullet in `docs/stories/A16-owner-checklist.md`'s trial section. The trial now also reports:
- the day's 3 pm recorder result;
- any Groww sign-in error in either run.

It records the builder's two-sign-in check.

**The evidence (conversations commit 5c73738).**
- **The check:** read-only, at 21:38 IST.
  - Sign-in A, then a quote: ok.
  - 35 s later, sign-in B, then a quote: ok.
  - A's quote again, at once and one minute later: still ok.
  - The tokens differ, checked as a boolean.
- **What it printed:** status and error class names only, no token and no price.
- **The label:** the bullet labels it rightly as "some evidence: once, outside market hours", and leaves the confirmation
  to the in-market trial. That answers my note in section 2 in the simplest way: a recorded check plus a daily report,
  with no schedule change and no code.

**Register check.** The A16 builder owns this file (the "A16 routine" row), so there is no overlap.

### Verdict: PASS for 3cef31e35e1be3ee6fca1243f4aac95bb4c3d40a
