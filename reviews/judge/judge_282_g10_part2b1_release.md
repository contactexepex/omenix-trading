# Judge 282: G10 part 2 (b1), the release record, commitment times and the v4 fire workflow (story/g10-part2b-release at 74a604d2)

Judge B, 16 Oct 2026. Lane 1 (a workflow, Drive, the deadline). Text: judge 274 addendum 1. Builder: G10
(01VK88Lx).

**Verdict: FAIL.** One should-fix: the new workflow throws away the fire log.

## What holds

| Item | Result | Evidence |
|---|---|---|
| The release record (section 2) | MET | part 1's day format plus `pack_path`, validated by G8's own `parse_day` (one rule); a `pack_path` that does not fit the label is refused; `publish` writes the pack, then the record, through O9's `DataStore` (write-once); a `system_late` day writes the record only |
| Readers only through the verified cache | MET | `ReleasedPacks` needs a receipt, then `DriveCache.sync`, and refuses on any problem for that path (`NotReleased`); the pack is re-read with `read_pack` against the released SHA |
| The 15:10 deadline (section 5) | MET | `CommitmentTimes` over O8's evidence (F1's push receipts); an unknown or offset-free time raises, never guessed; 15:10:00 counts, 15:10:01 is a miss (UTC input tested). My plant (`<=` to `<`) fails 1 test |
| The fire workflow's trigger (section 6) | MET | a push of `receipts/data/v4/days/**` to `main` only, no schedule (test), and today's IST receipt only. My plant (the old path `receipts/v4/days/**`) fails 1 test |
| The text correction `receipts/data/v4/days/**` | **ACCEPT** | O9's `DataStore` puts every file under the `data` area, so the receipt is `receipts/data/v4/...`; the test computes it from O9's `ReceiptFolder`. My judge 274 text had the shorter path |
| Composition root listed in CLAUDE.md | MET | `fno/v4_pack/wiring.py` |

## Should-fix: the fire log is never committed

`v4-fire.yml` runs `python -m fno ai fire --day <today>` and asks for `contents: write` "for the fire log", but no
step commits or pushes anything. `ai fire` does not commit its own log (`fno/ai/fire.py`: "the fire log ... committed
with the records after 15:15"). In v2, forecast-capture's commit step does it (`git add research/forecasts # ... and
the fire log`).

On this new job the log dies with the runner. Everything downstream reads it:
- `collect` and `reveals-ready` (which books were fired);
- BG1's `capture_coverage.fired_sessions`;
- F8c's not-captured alerts (judge 276).

A v4 fired day would look unfired: no alert, and the meter would not see the session.

The fix is the builder's design. Either a commit-and-push step for the fire log path (`git pull --no-rebase` first,
the record scan on), or a stated and tested hand-off to the job that commits it, plus a test that the workflow commits
the log's path.

## Merge timing (agreed)

The workflow calls G11's `ai fire --day`, which is not on `main` yet. Nothing pushes a release receipt until part (b2)
runs in the routine, so it cannot trigger early. Still, merge (b1) only after G11's v4 fire lands, as the builder
proposes. (b2) also waits for the orchestrator's A2 decision (judge 274 note).

**Gates (run by me on 74a604d2):** 7,801 passed, no failures. `ruff check`: clean. `ruff format --check`: 1,407
files already formatted. `check_imports`: clean.

## Addendum 1: story/g10-part2b-release at be7322b1 (number 282.1, claimed with `tools/claim_number.py`)

**PASS.** The should-fix is met:
- `v4-fire.yml` sets a commit identity with the record scan on (`core.hooksPath .githooks`) before the fire.
- After the fire (`!cancelled()`, only on a day with a release), a "Commit the fire log" step runs
  `git add research/forecasts/ai_v4`, commits when something changed, then `pull --no-rebase` and `push origin
  HEAD:main`. There is no `--no-verify`.
- A test pins the order, the path, the pull and push, and the hook config. My plants (the commit step removed; the
  hooks line removed) each fail 1 test.

The fire line is now `ai fire --protocol v4 --day`, since plain `ai fire` stays v2's until the freeze (G11).

**Merge conditions (recorded):**
1. Merge only after G11's v4 fire lands. Both `--protocol v4` and the fire-log path come from G11's branch.
2. G11's own test must check that `fired_v4_path` lies under `research/forecasts/ai_v4/`, the folder this workflow
   commits. The builder has asked G11; G11's code verdict will check it.

**Note:** if the fire dies before writing any log, `git add` of a missing folder fails the step. The failure alert
then posts once, which is the same outcome as the failed fire.

**Gates (run by me on be7322b1):** 7,802 passed. `ruff check`: clean. `ruff format --check`: 1,407 files already
formatted. `check_imports`: clean.

## Addendum 2: story/g10-part2b-release at 81311283, A2 dropped (number 282.2, claimed with `tools/claim_number.py`)

**PASS.** This covers the orchestrator's ruling (1), drop A2, made after my judge 274 note (90bc4565), together with
the fire-log fix already passed in addendum 1.

| Item | Result | Evidence |
|---|---|---|
| Code: A2 removed everywhere | MET | `V4_DAY_A2` deleted from constants; G8's `days.LABELS` is (A, system_late); `DayCounts` and the counts line have no A2; the pack codec's `PACK_LABELS` is (A,). No `V4_DAY_A2` or `a2` reference left in `fno`, `tools` or `tests` (grep at 81311283) |
| An A2 day file or pack is refused | MET | tests. My plants (A2 back in `LABELS`; A2 back in `PACK_LABELS`) each fail 1 test |
| Text: section 1.6 labels are A and `system_late` only | MET | `system_late` also covers "no release record at all"; a verdict uses A days; a dated note gives the three facts I confirmed in A16's code |
| The A path | MET | A4e's named capture (judge 281); only a sidecar with `clock_ok` gives A, anything else is `system_late` |
| G11's catch-up rule | MET (text) | each publisher run first writes `system_late` for every earlier scored session since `daily.live_from.forecasts_v4` with no record, so the look is never blocked forever; records stay write-once. The code is in (b2) |
| `days.py` lands before the freeze | noted | it is byte-checked at the v4 freeze |

**A condition for (b2)'s code (recorded, not a finding here):** the catch-up must decide "no record" from Drive (O9's
`DataStore` and its receipts), not from the checkout alone. If a day's release record is in Drive but its receipt is
not pushed yet, a catch-up that looked only at the checkout would try to write `system_late`. Write-once refuses that,
so it must fail by name, never overwrite and never crash the run. (b2)'s judge checks this with a test.

**Gates (run by me on 81311283):** 7,966 passed, 18 xfailed (from main), no failures. `ruff check`: clean. `ruff
format --check`: 1,441 files already formatted. `check_imports`: clean. Main has moved on since. Merge after G11's v4
fire (addendum 1's condition), with a pull and the full suite on the merged tree.

## Addendum 3: may part 2b merge without G11's v4 fire? (number 282.3, claimed with `tools/claim_number.py`)

Asked by the orchestrator on 21 Oct. G11 is parked (the owner's focused-team choice), the v4 freeze (R2/G7, about 27-28
Oct) gives the AI slots p = 1 while G11 is not live, and part 2b must land before the freeze because `days.py` drops
A2.

**Ruling: YES, with one condition. `v4-fire.yml` does not land on `main` until G11's v4 fire does.**

Why the condition is needed:
- `v4-fire.yml` runs `python -m fno ai fire --protocol v4 --day ...`. Main's `fno/ai/cli.py` has no `--protocol`
  (grep on `origin/main`), so that step can only fail.
- The workflow is harmless only until part (b2) starts publishing. From the first day (b2) pushes a release record
  receipt in the routine, every push triggers it. Then argparse refuses, the fire-log step's `git add` of a missing
  folder fails, and "v4 AI fire (GitHub Actions) failed" posts to #fno-desk **every trading day** until G11 is
  unparked. That is a false alert on a normal path, and a workflow calling a command that does not exist is dead code.
- Nothing else in 2b needs G11. `fno/v4_pack/` (release, commitment, codec, guard), G8's `days.py` and the constants
  are used by no G11 code, and nothing on `main` reads a v4 AI fire log (grep: no other file names `v4-fire` or
  `ai_v4`).

How to land it (the builder's choice):
1. **Preferred:** take `.github/workflows/v4-fire.yml` and `tests/v4_pack/test_fire_workflow.py` out of the merge and
   carry them with G11's v4 fire. Their tests (the trigger path equals the release receipt path, no schedule, the
   fire-log commit after the fire with the record scan on) go with them unchanged, and so do my addendum-1 conditions.
2. **Or** land the workflow switched off (for example `workflow_dispatch` only, or a job-level `if: false` with a
   comment naming G11), with a test that it cannot run on push. The push trigger is restored in G11's merge.

Either way the rest of 2b (A2 dropped, the release record, the 15:10 commitment times, the pack codec and guard) may
merge now. Pull, run the full suite on the merged tree, and confirm `tools/check_numbers.py` is clean. Main has moved
five days since 81311283, so a full rerun is required, not optional.

The AI slots stay at p = 1 at the freeze while G11 is parked, which is the protocol's own rule for an unjudged member.
This ruling changes nothing there.
