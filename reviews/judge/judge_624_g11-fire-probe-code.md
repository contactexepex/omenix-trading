# Judge 624: G11 fire probe, one manual fire of Book 3's routine with a 24 KiB harmless text (story/g11-fire-probe at 714509261)

**FAIL, lane 1.** Round 1 of 2. Judge I, own session (session_01CHtddAzFcEdQh4HFiz3mqU), 25 Oct 2026. The code is
right; the one finding is in the story's Claims (quality rules 2 and 6).

## Criteria and the orchestrator's checks

| Check | Verdict | My evidence |
|---|---|---|
| 1 Never on a push or a schedule; read-only; no git, no write | MET | `on: workflow_dispatch` only, `permissions: contents: read`, no `git` in any run (workflow lines 8-12, 28-33); test `..._runs_only_by_hand_...`; my N2 (`git push`), N11 (`contents: write`), N12 (a `schedule`) caught |
| 2 Book 3's routine through the unchanged trigger; its two secrets, on the fire step only | MET | `cli._fire_probe` calls `build_book_trigger(BOOK3_AI)`; `fno/pipeline/trigger.py` is unchanged in the diff; env is on the fire step only (`pip install` never holds the token); N1 (token at job level) and N7 (Book 2's trigger) caught |
| 3 One line, one single quote at the end, 24 KiB, above 19.5 KB, under the cap; harmless | MET | `ProbeText.to_text`: exact 24,576 bytes (test); N3 (19 KiB), N4 (off by one), N10 (a second quote), N13 (cap check) caught. The stored prompt (`F1-G5-owner-checklist.md:42-43`) stops at step 2 on any single quote. Only step 0 (fetch and checkout) and step 1 (`git config`) run first, and neither writes |
| 4 The answer printed, never the token; exit 1 when not fired; a 4xx reported, not retried | MET | `RoutineFireTrigger.fire` posts once, with no loop and no retry (`trigger.py:49-65`), and maps 401/403/429/other to `FireFailed`. The ConnectionError test shows only the type, and the token is in neither stream. N5 and N6 caught |
| `NOT_WATCHED` entry | MET, justified | a deliberate refusal is the probe's answer, not a failed capture for O8/O10; without it `test_every_job_is_watched` fails (N8 caught) |
| Nothing recorded or counted | MET | no fire log, no commit, no slot: the probe calls only `trigger.fire`. The probe session's minutes are recorded nowhere, as the builder says |

## Findings

1. **Should-fix (quality rules 2 and 6): the Claims have no gap list and no real output sample.**
   - **Gap list:** the orchestrator's checks are mostly covered, but "a 4xx reported, not retried" and "secrets on the
     fire step only" are not named criteria. Both hold in the code and are pinned by tests (see above). Add a gap
     list that maps each check to a criterion, and add those two to criteria 2 and 4.
   - **Output sample:** add the line the committed code prints, for example from the test with a fake 200, and the
     413 line.
   - A docs-only fix, judged by reading in round 2.

## Plants

12 planted (N1-N8, N10-N13), one at a time on `tests/ai`, `tests/health` and `tests/pipeline`; each restored; tree
clean after. **12 caught, 0 survived.**

## Gates (714509261 merged with origin/main a54f1016d as 3eb1c7e0c, clean; FNO_SLACK_BOT_TOKEN kept)

- `ruff check` clean; `ruff format --check` 2632 files; `check_imports` clean (2761); `check_records` clean (9268).
- `python -m pytest -q -p no:cacheprovider -n auto`: **16559 passed, 1 skipped, 14 xfailed, 0 failed** (599 s).
- Slack in the run's window (22:37:34-22:47:34 UTC): #fno-forecast and #fno-intraday are empty. #fno-desk holds only
  labelled "DRY RUN" rehearsal posts built from real recorded days (21 and 22 Oct). No test posted.

## Notes (not findings)

- Rule 1: the text and the code arrived together, with no text round. The orchestrator routed this as code round 1.
- "Before anything runs" (`fire_probe.py:4`): steps 0-1 do run first. They are harmless, so the wording is loose but
  the effect is right.
- The step summary carries the session link. It is a private claude.ai link and not a secret.

## Addendum 1: round 2 at 8d5ad1ec3 (diff 714509261..8d5ad1ec3)

**PASS, lane 1** (Judge I, own session). The diff changes only `docs/stories/G-forecasts.md`; the code is the
714509261 I judged, with its 12 of 12 plants and the merged-tree gates (16,559 passed, 0 failed).

| Item | Verdict | My evidence |
|---|---|---|
| 624.1 should-fix: gap list | FIXED | Criterion 2 now says the secrets sit on the fire step only, and criterion 4 says a refusal is reported, never retried (one POST a run). With those, the orchestrator's six checks are all named criteria or Claims. The gap list states plainly what the probe does not prove (Book 2 assumed; the model's re-typing of a real pointer; no window guard; minutes unrecorded) |
| 624.1 should-fix: output sample | FIXED | Lines for 200, 413, 401, no network and missing secrets, labelled a LOCAL run against a FAKE endpoint, with one POST per case. They match the code's templates (`fire_probe.py` `FIRED`/`NOT_FIRED`, `trigger.py`'s refusal texts, the missing-secrets line pinned by the test) |

Doc-reading tests at 8d5ad1ec3, with `FNO_SLACK_BOT_TOKEN` kept: 922 passed, 14 xfailed.
