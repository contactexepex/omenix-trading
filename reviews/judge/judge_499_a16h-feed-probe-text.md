# Judge 499: A16h story text, a read-only probe of Groww's websocket feed

**Scope:** story/a16h-feed-probe at 2385ac62 (A16 builder session 01VK88LxJvV1Gi7Wbr3D4fzp), the story text only:
`docs/stories/A16-intraday-quote-recorder.md` section A16h and its register row. Judge I. Lane 1 (an outside service,
Groww), text first. Round 1 of 2.

**Verdict: FAIL.** 2 should-fixes, 2 minors. The design and the read-only guard are right; two windows put A16's own
marks, and with them the forecasts, at risk.

## Checked against the sources
| Point | Result | Evidence |
|---|---|---|
| The owner's decision | MET | DESK_DECISIONS 23 Oct, "Live data: test the Groww feed first"; research note `research/school/probes/2026-10-23-live-data-feeds.md`: buy nothing, a probe from Tue 27 Oct, never on 23 or 26 Oct |
| The allow-list matches the SDK | MET | the installed `growwapi.GrowwFeed` has exactly 20 public names: the 11 the text allows plus the 9 account-reading names it refuses. `__init__(self, groww_api: GrowwAPI)` takes the trading client, so building it only in the composition root is right |
| The pattern to reuse | MET | `fno/intraday/read_only.py` `ReadOnlyGroww` (a `__getattr__` allow-list, frozen `__setattr__`) |
| The orchestrator's two conditions | MET | `alongside` is capped at 1,000 and stops on any 429; the account names are named in a test (criterion 1) |
| No values, no schedule | MET | counts and times only; the note is written by hand; no schedule or workflow |

## Findings
1. **Should-fix: the `ramp` window sits on A16's 11:15 mark, while the text expects throttling.**
   - A16 marks every 15 minutes (A16 story line 141). A mark with no usable level voids that session's RV (line 201), the input of v4 and G14's forecasts.
   - The text's own known limit says a ramp to 3,000 "may draw throttling on Groww's side". On one shared key, that can cost the 11:15 mark, and so the day.
   - Fix expected, either:
     - ramp outside market hours, if a subscription refusal can be seen then (the text says how that is judged); or
     - ramp between two marks with a hard stop at least 2 minutes before the next one (e.g. 11:16-11:28), also stopping at once on any 429.
2. **Should-fix: `alongside` needs a go/no-go gate set by that day's morning evidence.**
   - Its 429 stop sees only the probe's own calls; the recorders' failures are invisible to it.
   - Its sign-in shares the recorders' key. Coexistence was seen only outside market hours (15 Oct).
   - A lost 3 pm capture costs a session of the desk, the school's five roads and G13.
   - Fix expected:
     - run `alongside` only if the same day's `coverage` run (which overlaps A16's 10:30 mark on purpose) left that mark and the 10:45 mark clean: no 429, nothing missing;
     - the probe signs in before 14:50 and never during 14:55-15:13;
     - a missed condition means no `alongside` that day, written in the note.

**Minor:**
- (a) `dir(GrowwFeed)` has no `place_`, `modify_`, `cancel_` or `create_` name today, so criterion 1's test of them is empty. It should also try such names itself (e.g. `place_order`).
- (b) The probe note should give coverage by class (index × expiry × option type: subscribed, ticked), not a per-strike list.

## Notes
- The terms question (whether Groww allows read-only use) stays open by the owner's choice (22 Oct). The text says so.

## Addendum 1: text round 2 at 59069906

**Verdict: PASS (text).** The code may start; the code round is judged against criteria 1-6 as now written.

- **Finding 1: ACCEPTED.** The ramp runs only from 11:17:00 to a hard stop at 11:28:00, and stops on any 429. A16's mark measures 53-57 s (A16 story, "One snapshot, measured"), so it clears the 11:15 mark with about a minute to spare, and the 11:30 mark by 2 minutes. Unfinished steps move to the next day. Choosing between marks over after-hours is reasoned: whether a refusal shows with the market closed is unknown.
- **Finding 2: ACCEPTED.** `alongside` runs only after a clean 10:30 and 10:45 A16 mark from that day's `coverage` run, signs in and subscribes before 14:50, and makes no new sign-in during 14:55-15:13. A missed condition means no run that day, with the reason noted. Criterion 3 now tests the refusal.
- **Beyond the ask:** every plan stops on its own 429 or at its hard end time (criterion 3).
- **Minors (a), (b): ACCEPTED.** The test supplies the trading names itself; coverage is reported by class.
- **For the code round:** I will plant faults on the gate (a 429 in the ledger, a missing mark, a start at 14:51), on the hard end times, and on each allowed and refused name.

## Addendum 2: the ramp's new window at f1b4fca9

**Verdict: PASS (text), with one condition for the code round.** f1b4fca9 changes only the ramp's window, as the
orchestrator directed. First choice: after the close, from 15:45, once A16's 15:30 mark is on `main`. Fallback, if Groww
refuses subscriptions after hours: 10:50:00-10:58:00 chunks, between the 10:45 mark (about 53-57 s) and the 11:00 mark.
Both windows avoid every A16 mark. Reading a refusal at 500 twice as "closed market", not as the limit, is sound.

- **Condition (to hold in the code):** A16b's candle catch-up (`intraday backfill`) also uses Groww on the shared key, from 15:33 in the daily run (CLAUDE.md, O1 step 2).
  - The after-close ramp must not start until that day's catch-up step is recorded done in `journal/runs/<date>.json`.
  - A ramp started early refuses with one named line, with a test.
  - I will plant faults on it in the code round. The builder may add the line to the text then.

## Addendum 3: the orchestrator's two questions on f1b4fca9

1. **Does 15:45 collide with other Groww users? Yes, possibly.** A16b's catch-up starts at 15:33 on the same key. That is Addendum 2's condition for the code: the ramp starts only once the day's catch-up is recorded done.
2. **Is a refusal at 500, twice, a sound reading of "market closed"? Not by itself.** It cannot tell a closed market from a real limit under 500. That day's `coverage` run already held about 400 subscriptions, so a limit between 400 and 500 would look exactly like "closed". Second condition for the code:
   - The after-close ramp's first step is small (50). A refusal at 50, twice, reads as "closed market".
   - 50 accepted but 500 refused reads as a limit under 500. The ramp then halves its way down from there (e.g. 250, 375, ...) and reports the bounds; it is never read as "closed".
   - In the fallback window, a refusal at the first step is reported as a limit, since the market is open.
   - Tests: a fake feed that refuses everything gives "closed"; one that refuses at 450 gives "limit between 400 and 450" (or the bounds reached).

## Addendum 4: instrument tokens at 214bdeb7

**PASS (text).** The tokens come from the SDK's `INSTRUMENT_CSV_URL`. In the installed SDK that is
`https://growwapi-assets.groww.in/instruments/instrument.csv`, read with a plain `requests.get` and no credentials
(`growwapi/groww/client.py:115,179`), so it spends none of the key's limits. The at-the-money strike comes from 4
`get_quote` calls through the existing `ReadOnlyGroww`, with no change to the allow-list. Two conditions for the code:

- **The URL is read in the composition root (or copied into a named constant there), never by naming `GrowwAPI` elsewhere** (criterion 2).
- **In `alongside`, the instrument list and the 4 `get_quote` calls happen before 14:50**, with the sign-in. Nothing touches the key during 14:55-15:13.

## Addendum 5: code round 1 at ef896e21 (diff 214bdeb7..ef896e21)

**Verdict: FAIL.** 3 should-fixes: the three code conditions of Addenda 2-4 are not in the code. Criteria 1, 2, 4 and
5 are met, and criterion 3 partly.

**Met (my checks):**
- **The guard:** `ReadOnlyFeed` lets exactly the 11 names through; the 9 account names and 4 supplied trading names are refused; it cannot be changed. The test pins the SDK's own name list. 4 plants caught.
- **The gate:** `feed_gate.py` reads A16's ledger (`mark_ist` "10:30"/"10:45", status, failures, recorded against expected) and runs before any sign-in. 3 plants caught.
- **The plans:** each plan's window and cap are checked; any error, a 429 included, stops the plan, unsubscribes everything and is named by class only. Plants caught: the window moved to 14:51, the cap at +1, the unsubscribe dropped, a wait past the end.
- **Gates (my run):** full `pytest -n auto` 11,705 passed, 16 xfailed, 0 failed; ruff check and format, check_imports clean.

**Findings:**
1. **Should-fix: the after-close ramp does not wait for A16b's catch-up (Addendum 2).** Nothing in `feed_cli.py` or `feed_probe.py` reads `journal/runs/<date>.json`. The `ramp` plan may start at 15:45 while the catch-up still uses the shared key.
   - Fix expected: refuse to start until that day's catch-up step is recorded done, with one named line and a test.
2. **Should-fix: the ramp cannot tell a closed market from a limit under 500 (Addendum 3).** `RAMP_STEPS` starts at 500, and a refusal at 500 is reported as plain "failed".
   - Fix expected: start at 50 after the close; a refusal at 50, twice, is "closed market"; 50 accepted with a later refusal halves down to its bounds.
   - Tests: a feed that refuses everything, and one that refuses above 450.
3. **Should-fix: a late `alongside` start signs in and quotes inside 14:55-15:13 before it is refused (Addendum 4).** `cmd_feed_probe` builds the client (`build_feed_probe`, a sign-in) and calls `get_quote` four times (`build_universe`) before `probe.run` checks the window.
   - Started at 14:56, it touches the shared key in the recorders' window and only then refuses.
   - Fix expected: check the plan's window in the command before any sign-in, as the gate already is, with a test whose clock reads 14:56 and which shows no sign-in.

**Minor:**
- Plant `while clock < end + 1 minute` hangs the tests instead of failing them (the fake clock stops at the end). A hard-end test should fail, not hang.
- `feed_cli.py` cuts `alongside` to its first 1,000 instruments instead of refusing more. That is safe, but the sample is whatever comes first in the universe; the note should say which classes it holds.

**Plants:** 11 planted: 10 caught, 1 hangs (minor above).

## Addendum 6: code round 1 at 4abcf179 (the orchestrator counts ef896e21's Addendum 5 as no round)

**Verdict: FAIL.** 1 should-fix, 1 minor. Addenda 2 and 3 are built and right; Addendum 4's key point is not.

- **Addendum 2: MET.** `feed_gate.catch_up_gate` reads `journal/runs/<date>.json` (`steps.candles.finished_at`, the same shape as the real 22 Oct log), and the command checks it before any sign-in. Plants caught: the finished check removed, the gate not wired for `ramp`.
- **Addendum 3: MET.** `feed_ramp.py`:
  - the steps run 50, 500, ...;
  - after the close, 50 refused twice means a closed market; between marks, the first refusal is a limit;
  - a refused batch is released, and a limit is halved down to within 50;
  - a 429 stops the run.
  Plants caught: no retry at 50, no halving, steps from 500, a 429 swallowed, the release dropped, a partial batch accepted.
- **Gates (my run):** full `pytest -n auto` 11,716 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean.

**Finding:**
1. **Should-fix: a late start still signs in before its window is checked (Addendum 4; the orchestrator's point).**
   - `cmd_feed_probe` calls `build_feed_probe` first. Its `GrowwFeed(provider.api)` evaluates `provider.api`, which calls `get_access_token`: a sign-in on the shared key (`providers/groww.py:140-157`). Only then does it call `probe.check_start`.
   - An `alongside` started at 14:56 signs in inside the recorders' 14:55-15:13 window and only then refuses. The instrument list and the quotes now wait, but the sign-in does not.
   - My plant (the command's `check_start` removed) survives: no test checks the order at all.
   - Fix expected: check the plan's window in the command before `build_feed_probe` (a clock-only check, as the gates are). Test: at 14:56 the command refuses and builds no client (a fake `build_feed_probe` that fails if called).

**Minor:** the catch-up gate accepts a `candles` step that finished as failed. A rerun of the daily run may then retry it beside the ramp. Requiring `result.status == "ok"` closes that.

**Plants:** 9 planted, 8 caught. The survivor is finding 1.

## Addendum 7: code round 2 at 947aee82 (diff 4abcf179..947aee82)

**Verdict: PASS.** The code may merge under the merge procedure; the first probe is Tue 27 Oct, by hand.

- **Finding 1 (Addendum 6): FIXED.** `cmd_feed_probe` first calls `window_refusal(plan, day, now)`, clock-only, before the gates, `build_feed_probe` (so before `provider.api` and `get_access_token`) and `build_universe`. `test_a_start_outside_the_window_is_refused_before_any_sign_in_or_quote` traps the sign-in, quotes and gates at 10:26, 14:56 and 16:01. My round-1 survivor (the check removed) is now caught.
- **Minor: FIXED.** The catch-up gate requires `result.status == "ok"` (plant caught); a cut names what it kept.
- **Plants this round:** 5 planted, 3 caught. Both survivors are equivalent, not gaps:
  - the second `check_start` after the sign-in, removed: the first check and `run`'s own window check still refuse;
  - the watch loop running past its end: `wait()` returns False at the hard end, so the loop stops there anyway.
- **Gates (my run):** full `pytest -n auto` 11,722 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean.

## Addendum 8: the TLS fix at 94c7ca18 (story/a16h-feed-tls, on main 2c215d74)

**Verdict: FAIL, round 1 of 2.** 1 should-fix. The design is right; its key wiring line has no test.

**Checked (my evidence):**
- **Root cause confirmed.** The installed `growwapi/groww/nats_client.py:120` builds `ssl.create_default_context(cafile=certifi.where())`, ignoring `SSL_CERT_FILE`. My own handshake to `socket-api.groww.in:443` from this container:
  - certifi alone: `CERTIFICATE_VERIFY_FAILED` (self-signed certificate in chain);
  - certifi plus `SSL_CERT_FILE` (`/root/.ccr/ca-bundle.crt`): `handshake ok TLSv1.3`, with `CERT_REQUIRED` and hostname checking on.
- **Orchestrator's condition 1: MET in `feed_ca_file`.**
  - certifi's roots plus the bundle, in one file, never replacing them;
  - no bundle, no change;
  - only the SDK's feed module is given the file.
  - The tests make real localhost TLS handshakes: a certificate from the added CA verifies, and an untrusted one is still refused.
  - Plants caught: the bundle replacing certifi, the bundle dropped, a missing file accepted.
- **The patch takes effect at connect time:** the SDK calls `certifi.where()` inside `_connect`.
- **Building in a worker thread is safe:** `NatsClient` owns its own event loop and consume thread, and later calls use `run_coroutine_threadsafe` on that loop.
- **Orchestrator's condition 2: MET.** `open_feed` gives up after 30 s with one line; a connect error is named by class only. Plants caught: no timeout, the error swallowed.
- **Gates (my run):** full `pytest -n auto` 14,333 passed, 16 xfailed, 0 failed; ruff check and format, check_imports and check_records clean.

**Finding:**
1. **Should-fix: the fix's own wiring is untested.**
   - My plant removes `if ca_file: trust_for_feed(nats_client, ca_file)` from `build_feed_probe` (`feed_wiring.py:48-49`), and all 41 feed tests still pass. That puts back the exact 23 Oct failure.
   - Fix expected: a test of `build_feed_probe` with fakes for the provider and `GrowwFeed`, and with `SSL_CERT_FILE` set. It checks that `nats_client.certifi.where()` then returns a file holding both bundles, and that without `SSL_CERT_FILE` the module keeps the real certifi. Restore the module after the test.

**Notes (no action):**
- **Trust anchor:** with the proxy's CA trusted, the proxy is the trust anchor, as it already is for every HTTPS call in this environment. My handshake with a wrong name was accepted too, because the proxy mints a certificate for whatever name is asked. The SDK's own hostname check still runs against what the proxy presents. That is an environment property, not a defect here; on a host without `SSL_CERT_FILE`, certifi alone is used.
- **Leftovers:** each run leaves one `feed-ca-*` temp folder holding public certificates only. A connect that times out leaves a daemon thread retrying until the process exits, right after the stop line.

## Addendum 9: TLS fix round 2 at f0b72a93

**Verdict: PASS.** It may merge under the merge procedure.

- **Finding 1 (Addendum 8): FIXED.** `test_the_built_probe_connects_with_the_combined_roots_only_when_a_bundle_is_set` calls `build_feed_probe` with a fake provider and a fake `GrowwFeed` that records `nats_client.certifi.where()` when built. With `SSL_CERT_FILE` it gets the combined file; without it, the real certifi; monkeypatch restores the module.
- My Addendum 8 plant (the `trust_for_feed` call removed) now fails it.
- The diff is the test and the story's Claims only; no code changed since 94c7ca18, whose full suite I ran (14,333 passed). The 10 TLS tests pass at f0b72a93.
