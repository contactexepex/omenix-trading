# Judge 57: P5b contract follow-ups, code (one judge, judge #2)

Branch `story/P5b-contract-followups`, SHA `37ab00d`, compared with base `dea8d78`. Lane 1. **FAIL** (round 1) on 1
should-fix, tests only. Parts (1) and (2) are sound. In part (3) the swap preserves behaviour, but the seven callers'
commit-failure behaviour is not pinned by any test, contrary to the request's claim.

## Gates (`__pycache__` cleared)

892 passed; ruff and imports clean.

## (1) The W2 and W4 direct tests: MET

`python tools/contract_plants.py W2 W4` gives `W2: ok`, `W4: ok`. Each plant (W2: write in place with no temporary
file; W4: the receipt digest check removed) is caught, now also by the new direct tests in `test_write_once_layers.py`.
- W2: a write that dies midway leaves nothing under the real name.
- W4: `ReceiptFolder` refuses a different digest by itself, and the same digest keeps the first receipt (its
  `written_at` is unchanged).

Both tests are non-vacuous.

## (2) The guard as an allow list: MET

I ran 15 shapes through `problems()` (scratch script, not committed). Every one gave the expected result.
- **Accepted:** a pair as the last command, `|| exit 1`, `|| exit 2`, and the retry loop.
- **Flagged:** `|| exit 0`, `|| echo failed` (my earlier gap, now closed), `|| true`, `|| :`, `; exit 0`,
  `&& exit 0` outside a loop, `|| exit "$code"`, a later command, `|| exit 1; echo`, a continuation followed by
  `exit 0`, and a subshell followed by a command.

## (3) The seven callers on `commit_failed`

- **Behaviour preserved, by reading:** each swap replaces `<MARK> in line` with `commit_failed(line)`.
  - Every committer in `fno/` is a `GitManifestRecorder` with a label (for example `close_read/wiring.py:32-36`,
    `data_wiring.py:38-41`). So every failure line contains " NOT committed" with its leading space, and the three
    callers that used "NOT committed" without the space match the same lines.
  - The `preopen_cli` text is unchanged: `f"pre-open receipts{NOT_COMMITTED_MARK}: ..."` with the leading-space mark
    gives the same "pre-open receipts NOT committed: ..." as before.
  - `grep` finds no other "NOT committed" match site in `fno/`. Exit codes and alerts are the same code paths.
- **But no test pins it. S1:** in each caller I replaced the check with "never failed". **All nine plants survive at
  892 passed:**
  - `circulars/job.py`, `close_read/cli.py` and `flow_history/cli.py`;
  - `fo_masters/job.py`;
  - `global_cues/preopen_cli.py` (the check, and also the message text);
  - `preopen/record.py` (the early-file commit and the day commit);
  - `storage/repair_cli.py`.

  `test_callers.py` covers CF1's own callers, not these seven. On the base `dea8d78` the same plants survive
  (`close_read`, `fo_masters` and `repair_cli` checked), so this gap is older. The only guard there was the
  string-equality test (changing the `fo_masters` mark failed 1 test), and this diff removes it, rightly, since the
  strings are gone.

## Finding

1. **S1 (should fix, tests only): pin each of the seven callers on a failed commit.** These are live commit paths: a
   regression that drops one check would make a failed commit end green, with no alert, which is exactly what CF1
   exists to prevent. For each caller, add one test that feeds a committer returning the real `NOT_COMMITTED`
   line (formatted from the template), and assert the caller's existing reaction:
   - `closes`, `repair receipt`: exit 1;
   - `fo-masters`, `circulars`: the failure listed, the alert sent and exit 1;
   - `flows table`: the problem line and the alert;
   - pre-open early and day commits: a `commit failed` problem;
   - `preopen_cli`: `_committed` returns False, and an exception gives the exact "pre-open receipts NOT committed:
     <Class>" text.

   The nine plants above must then fail. `test_callers.py`'s real-lines helper can supply the line.

## Note (not blocking)

`COMMIT_FAILED_ALERT` itself contains " NOT committed or pushed", so it matches `commit_failed`. No caller feeds an
alert outcome back into the check today. But a future caller that collects "every printed line" (alert echoes
included) and then checks them would see a failure. A test that the alert text does not match, or a different
wording ("were not committed"), would remove the trap.

**Verdict: FAIL** (round 1). S1 is tests only; the code change is behaviour-preserving.

## Addendum 1: the orchestrator's added checks (37ab00d; still FAIL, round 1)

The orchestrator's brief arrived after the verdict above. Its extra checks:

1. **"No module keeps its own copy" is weak (note, folds into S1).** The test looks for module names that start with
   `NOT_COMMITTED`. Plant: a literal `' NOT committed' in committed` put back in `fo_masters/job.py` under no name. It
   passes all 892 tests. A source scan (no `NOT committed` literal in `fno/` outside `manifest_commit.py`, docstrings
   aside) would catch it. Together with S1's behaviour tests, that pins both how a caller detects a failure and what it
   does about it.
2. **S2 (should fix, text or test): the W2 row says more than is tested.** The row's "Where" column lists both
   `LocalFolderStore.put` and `_write` in `drive_cache.py`, and its status is "tested, plant run". The plant column
   honestly says the plant is on `LocalFolderStore.put` only. Plant: `_write` in `drive_cache.py` writing straight to
   the real name passes all 892 tests. So the `_write` half is still stated only. Either split the row (W2a tested,
   W2b stated only, with W2b in `EXPECT_SURVIVE`), or add a direct test for `drive_cache._write` with its plant.
3. **S3 (should fix, test): the invariant forbids any future "stated only" row.** `test_record_contract.py:64` asserts
   `stated_only_rows() == set()`. The correct invariant, `set(tool.EXPECT_SURVIVE) == stated_only_rows()`, is at line
   77 and is enough on its own. Plant: one row's status set to "stated only" fails 2 tests, the hardcoded empty-set
   check among them. So even with `EXPECT_SURVIVE` updated honestly, the hardcoded check still refuses it, which
   makes it too strict. Drop the `== set()` line and keep the 500-line check. Without that, S2's split cannot even be
   expressed.
4. The guard (another suppressor) and the W4 bite are covered above: MET.

**Verdict: FAIL** (round 1): S1 (the seven callers' tests), S2 (W2's scope) and S3 (the hardcoded invariant). All
three are tests or text.
