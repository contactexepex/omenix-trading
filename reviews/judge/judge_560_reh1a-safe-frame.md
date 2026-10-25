# Judge 560: REH1a, the rehearsal mode's safe frame, story/reh1-rehearsal

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1, round 1 of 2. One of two judges: E covers git,
  Slack and the HTTP and pre-run guards; B covers the clock, Drive and imports.
- **Head judged:** b2e5337d, merged with main as a7e17490 for testing
- **Claims:** docs/stories/REH1-rehearsal-mode.md, "Claims / REH1a"
- **Verdict: FAIL.** Three safety checks have no test, one of them the HTTP guard's install itself. The
  design holds.

## Gates (merged tree)
- pytest -n auto: 14859 passed, 0 failed.
- ruff check, ruff format --check, check_imports, check_records: clean.

## Findings: 3 of 18 plants pass the whole suite (14,859 passed with each in place)
1. **F1 (blocking): H3, the HTTP guard is never installed, passes every test.**
   - The plant: `process.install_process` keeps the replay clock but skips `http_guard.install()`.
   - The pre-run guard checks `allowed()`, a pure function, against its probe URLs. It never checks that a
     step's process actually has the guard in place.
   - Pin it at the real entry point: a `python -m fno` child with `FNO_REHEARSAL` set must refuse a
     `requests` call to a live host.
2. **F2 (blocking, the orchestrator's "never --no-verify"): G5, the data commit made with `--no-verify`,
   passes every test.**
   - `check_hooks` proves only that the config is set, not that the scan runs.
   - Pin it: a staged finding in the rehearsal clone's data commit, or in a step's commit, must be refused
     by the clone's hook.
3. **F3 (blocking): H5, a guard that crashes treated as clean, passes every test.**
   - The plant: `_guard` returns `[]` when its child exits non-zero, so the rehearsal runs with no checks.
   - Pin it: a guard child that fails must stop the rehearsal before any step.

## Checked and right: 15 of 18 plants caught
- **Git:**
  - `publish` pushes only `refs/heads/rehearsal/<day>-<run_id>`; the ref check (G1) and a push of main
    (G2) are both caught.
  - Every step's `HEAD:main` lands in the local bare origin; G3, leaving the clone's origin at the source,
    is caught.
  - The hooks path is set and checked; G4 is caught.
  - Every committer pushes `origin` from a root that resolves to the clone (`ROOT` comes from `__file__`):
    numbering, AI transport, manifests, receipts and the record store.
  - All of GitHub's push-triggered workflows are limited to `main`, so a `rehearsal/` push starts none.
- **Slack:**
  - The alerts, the card and the lab's poster are each labelled, and each port has a single posting
    method. S1 to S3 are caught; S4, the label without "DRY RUN", is caught.
  - No other posting path exists. The only other token use is `lab channels`, which reads
    `conversations.info` and posts nothing.
  - The record-scan hook alerts through `build_alert_sender`, so it is labelled.
  - There is no #fno-intraday poster yet.
- **HTTP:**
  - The guard refuses `requests`, `urllib` and `http.client`, Slack reads included: probed live.
  - H1 (GitHub API allowed), H2 (connect unchecked), H7 (any Slack path) and H9 (refusal raised as an
    OSError, which urllib would retry) are all caught.
  - The pre-run guard's probes (H4), the builder forms (H8) and stopping on a problem (H6) are all caught.

## Minor (for REH1b and REH1c)
- A probe shows that `urllib3` used directly and raw sockets pass the guard.
  - Nothing in the daily run uses them today: Groww's feed (NATS) first logs in through `requests`, which
    is refused, and psycopg runs only in the market-publish workflow.
  - REH1c's routines must keep it that way, or the guard must widen.

## Addendum 1

- **Head checked:** c37804a9, round 2 of 2: d362737c (judge 557) and c37804a9 (this report). Merged with
  main as 4642646b for testing.
- **Verdict: PASS (my half). Merge once judge B also passes.**
- **Gates:** pytest -n auto: 14999 passed, 0 failed. ruff check, ruff format --check, check_imports and
  check_records: clean.
- **F1 fixed:** `python -m fno rehearse check` runs in a real `python -m fno` child with the mode set.
  - It must see the replay clock and have a live `requests.get` refused.
  - `daily run --rehearse` runs it before the first step.
  - Plant H3 (`http_guard.install()` → `pass`) now fails tests/rehearsal/test_process.py.
- **F2 fixed:** a marker hook proves that the clone's data commit runs the record scan. Plant G5
  (`--no-verify`) now fails.
- **F3 fixed:** `_guard` stops on any non-zero exit, whatever was printed. Plant H5 (the exit code ignored)
  now fails.
- **Minor:** a urllib3 backstop is promised in REH1b's follow-up; raw sockets stay a stated limit.
