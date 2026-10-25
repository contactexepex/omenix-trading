# Judge 566: REH1e, the rehearsing parent carries the mode, story/reh1e-parent-env

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1, round 1 of 2. One of two judges: E covers point
  (a) and the parent audit.
- **Head judged:** 8246ddcf, merged with main for testing
- **Claims:** docs/stories/REH1-rehearsal-mode.md, "REH1e"
- **Verdict: PASS (my half). Merge once judge B also passes.**

## The leak, and my miss
DRY2's first real rehearsal posted one #fno-desk alert without the label. It came from the record-scan hook
on the parent's checkout commit: the parent's own git ran without `FNO_REHEARSAL`. My judge 560 checked
that the hook alerts through `build_alert_sender`, and so is labelled whenever the mode is set. It did not
check that the parent's own processes carry the mode. That path is now closed and pinned.

## Gates (merged tree)
- pytest -n auto: 15108 passed, 0 failed.
- ruff check, ruff format --check, check_imports, check_records: clean.

## The parent audit (code read)
- **Before the mode is set:**
  - `daily run --rehearse` returns into `rehearse_daily` before any day lock or alert is built.
  - `rehearse` then runs only `_is_session`, the local calendar, before `in_this_process(mode)` sets the
    mode in the parent's `os.environ`.
- **Inside the mode, every process inherits it:**
  - the unshallow fetch, clone, restore, `git rm` of files moved since, the data commit with its
    record-scan hook, and the push to the local bare origin (all via `run_git`, which inherits
    `os.environ`);
  - the guard child and the routine's children (their env is built from `os.environ`);
  - `commit_receipts` (env passed).
  - An alert from any hook therefore goes through the labelled sender.
- **`publish`:** only `refs/heads/rehearsal/...`, from the bare origin. The bare has no active hooks except
  the local post-receive log, and no push-triggered workflow matches a non-main branch (judge 560).
- **Restore:** the parent's earlier environment comes back afterwards.
- **What remains outside the mode:** the parent's own Python never installs the HTTP guard (its
  `install_process` ran before the mode existed). It makes no HTTP call of its own: only git to GitHub, for
  the unshallow fetch (a read) and `publish`.

## Plants: 5 of 5 caught (on the REH1 tests: 72 passed with each, 1 failed)
- E1: `rehearse` without `in_this_process`.
- E2: the mode not written into the parent's environment.
- E3: the parent's environment not restored.
- E4: files moved since the replayed day kept in the checkout.
- E5: the parent's git stripping the mode from its children.

## Note
If a later change makes the parent's Python itself post or fetch, it must install the HTTP guard inside
`in_this_process`.
