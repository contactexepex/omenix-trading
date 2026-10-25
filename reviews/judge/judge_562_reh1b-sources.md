# Judge 562: REH1b, the daily run's recorded sources, story/reh1b-sources

- **Judge:** E (session_01HkXMVPDEqVsmJZtghFrGzM), lane 1, round 1 of 2
- **Head judged:** 311bc999, merged with main as 5f11ee13. Since then 5dfbd936 adds only REH1a's round-2
  merge (d362737c), so the findings stand.
- **Claims:** docs/stories/REH1-rehearsal-mode.md, "Claims / REH1b"
- **Verdict: FAIL.** Two of the orchestrator's three points are untested in their wiring. The code itself
  reads right.

## Gates (merged tree)
- pytest -n auto: 15021 passed, 0 failed.
- ruff check, ruff format --check, check_imports, check_records: clean.

## Findings: 4 of 6 plants pass the full suite (15,021 passed with each in place)
1. **F1 (blocking, point a): B1, the receipts read from GitHub during a rehearsal.** `rehearsed_receipts`
   returning the real `GitHubActivityReceipts` passes every test.
   - In a rehearsal the HTTP guard would refuse api.github.com, so the seal fails closed and nothing leaks.
     But the seals would then never use the push log, and the claim "the receipts come from the rehearsal
     origin's push log" has no pin.
   - Pin: with the mode set, `build_seal_check`, or one of the five receipt builders, returns
     `LocalPushReceipts` over `<state>/pushes.log`.
2. **F2 (blocking, point b): B4, the git shim left off the steps' PATH.** Dropping `"PATH": path` from
   `rehearse_daily`'s child environment passes every test. Every step's commit would then carry the wall
   clock (the day after), and both D3's late rule and G13b's seals would judge the commits wrongly.
   - `test_git_dates.py` tests only the shim itself.
   - Pin: the environment `rehearse_daily` passes to its child puts the shim first. Better, a commit made
     through that environment is dated by the replay clock.
3. **Minor: B2, `_held` always False, survives.**
   - On a time-ordered log that logs every push to main, the first push whose `new` holds a commit is
     the one that brought it, so this plant is close to equivalent.
   - A test with a re-pushed or out-of-order line would pin it.
4. **Minor: B6, the push log counting every ref, survives.** Only `HEAD:main` reaches the bare origin
   today.

## Checked and right
- **(a) Receipts:** all five builders are wrapped by `rehearsed_receipts`: seals, AI, card, health and
  v4 pack. The real `GitHubActivityReceipts` is chosen only when there is no mode.
- **(b) The shim exists only in a rehearsal:**
  - `install_git_shim` has one caller, `rehearse_daily`. It writes the shim into
    `<rehearsal>/<run_id>/bin` and puts it only on the child environment's PATH.
  - The parent's `publish` uses the plain git.
  - B3 (the shim dates by the wall clock) is caught.
- **(c) No new path out:**
  - NSE's archive gets `NotRecordedSession`, which never sends anything (B5 caught; the guard's builder
    check covers it).
  - The recorded quotes, closes and candles read the real Drive through `RecordReader`, read-only.
  - The post-receive hook and the shim are local shell.
  - The guard gains probes for NSE's archive and GitHub's activity API.

## Plants: 6 planted, 2 caught (B3, B5), 4 survived (B1, B4 blocking; B2, B6 minor)

## Addendum 1

- **Head checked:** 67e150e3, round 2 of 2, merged with main. It also carries REH1a's merge, O9's
  8214a5d5, judge 559's notes and the urllib3 backstop.
- **Verdict: PASS (my half). Merge once judge B also passes.**
- **Gates:** pytest -n auto: 15060 passed, 0 failed. ruff check, ruff format --check, check_imports and
  check_records: clean.
- **Plants re-run by me, each fails 1 test now:**
  - **B1 (receipts from GitHub):** v4's real builder, with the mode set, returns `LocalPushReceipts` over
    `<state>/pushes.log`, and all five builders are held to `rehearsed_receipts`.
  - **B4 (the shim off the PATH):** a step's commit made through `rehearse_daily`'s environment carries
    14:05 IST on 23 Oct.
  - **B2 (`_held` always False):** a commit already held before a push is not received by that push.
  - **B6 (every ref logged):** only pushes to main are logged.
