# Judge 34: R1d plan (`docs/stories/R1d-groww-and-the-rest.md`), judge #1

**SHA:** `b3891f86a480009fe4ac39ff0e34bdf8a1d46b61` (`story/R1d-plan`). The diff from its base 4fb6d99 is docs only:
the new R1d plan (69 lines) and three R1c text fixes. Lane 1.

**Verdict: FAIL, one safety-relevant gap in the plan (text fix).** Everything else checks out.

## Checked and right (strong evidence: each read at this SHA)

**Rulings section.** It records what the orchestrator states it ruled:
- R1d1 is in process only, with no log and no alert.
- R1d2 is PARKED, with the three owner questions.
- R1d1, R1d3 and R1d4 are behaviour-preserving, one in judge-flight at a time.

Its premise "no workflow calls Groww" is true. No `.github/workflows/` file runs a Groww command, and
`quote-recorder-nse.yml:44` installs no broker SDK. Groww runs only from the Claude routines.

**R1d2.** It is marked PARKED in the split. The plan claims no cross-process Groww budget: "nothing about R1d2 is
designed or built". It also states that today's 150-a-day figure is an estimate (`groww_sign_in.py:8-11`: 38 processes,
114 tries).

**"Today" table rows, against the code.** These rows are right:

| Row | Code |
|---|---|
| Candle gap | `MIN_GAP_SECONDS = 0.5` (`candle_source.py:18`) |
| Intraday spacing | `RatePacer` with a lock (`pacing.py:11-14`) |
| Groww 429 pause | `PAUSE_SECONDS = 60` (`groww_rate_guard.py:17`) |
| Sign-in | 5 then 10 minutes, `TRIES_A_DAY = 3` |
| Close read | 3 tries, 60 s, no wait after the last (`reader.py:96-108`, `constants.py:12`) |
| Filings probe | 2 tries, 30 s after each failure, the last included (`filings/cli.py:21, 68-78`) |
| NSDL | 2 tries, `GAP_SECONDS = 10.0` |
| Global cues | `MAX_ATTEMPTS = 3` |
| Index loop | `RETRY_GAP_SECONDS = 60` |

Minor: the intraday rate is `PER_SECOND = 4` (`groww_source.py:36`). The plan's "4-5 a second" is loose.

**R1c folds.**
- `drive_only_store.py:49-63` is right: `get` runs from `:49` to `:63`.
- `drive_session.py:44-66` is right: `request` runs from `:44` to the `return` at `:66`.

**The 185/186 dispute: the implementer is right, and my nit was wrong.** At 60ab2d8 and at this SHA, `recorder.py:184`
is the `if` and `:185` is the none-marker `put`. I misread my own `sed` output. The doc stands.

**Test split.** It is a named lane-2 follow-up in R1c's follow-ups list.

## Required to PASS

### The quote recorders' Groww pacer is missing from the plan

Strong evidence: code read.

The table lists the intraday `RatePacer` and the candle gap. It omits the third and fourth Groww spacing users:
- `quotes/recorder.py:127`: `RatePacer(slot.per_second)`, "one per recorder, across attempts";
- `quotes/indices.py:25`: `INDEX_WORKERS, INDEX_PER_SECOND = 3, 2.5`, with the comment "with A16's 5 a second, under
  the about 10 where Groww began failing".

These are live capture windows (15:01-15:13 and the 3 pm quotes).

R1d1 as written says two things that conflict here:
- `RatePacer` becomes "the shared `RateLimit` (`groww`: 0.1 s spacing, 300 a minute)";
- condition 4: "one shared instance per process".

Read literally, both directions break today's behaviour:
- **One shared limiter per process.** The index recorders each have their own pacer today. Sharing one would slow
  their combined rate in the window, so fewer contracts are recorded before 15:13. That is weaker data completeness.
- **The host 0.1 s spacing alone.** A caller paced at 2.5 a second today could reach 10 a second, the rate where Groww
  began failing. That is weaker politeness.

The plan must say which it is. This is a safety-relevant ambiguity of the kind the orchestrator said would call a second
judge.

Fix (text only):
1. Add the quote recorder's row to the table (`quotes/recorder.py:127`, `quotes/indices.py:25`, one pacer per recorder).
2. State in R1d1 that each caller keeps today's own spacing as its own limiter: intraday 4 a second, candle 0.5 s,
   quotes `slot.per_second`, indices 2.5 a second. The host-level `groww` limit is only a ceiling that today's callers
   never reach.
3. Say how condition 4 ("one shared instance per process") applies. Either it is the 429 pause only, or the per-caller
   limiters stay one per recorder as today.
4. Add the matching never-weaker test to the gates: per-caller start spacing unchanged, and the combined rate of N
   index recorders unchanged.

## Hard lines

This is a plan document only: no code, data or service is touched. No secrets. No Groww call was made for this review;
it was code reading only.

## Addendum 1: d3cab04, round 2: FAIL, the shared 429 pause

Reviewed `d3cab04e19a4c834ce89f6079682ae0eaabf7db3`. The plan's diff from b3891f8 is the R1d file only (+23/-6). The
other files in the range are main merged in.

**My original gap is closed (strong evidence).**
- The quotes row is added.
- Each caller keeps today's spacing as its own limiter: intraday 4/s, indices 2.5/s, other slots their own
  `per_second`, candle 0.5 s.
- Condition 5 now specifies my item-4 tests: per-caller spacing unchanged, and the combined rate equals the sum.

**No host ceiling: the conclusion is right, the stated reason is not.** Today no host-wide Groww ceiling exists, so
adding none is never-weaker. But the plan's reason, "two callers in one process would sum to 6.5 a second (390 a
minute)", describes no real process. Every Groww command builds exactly one provider and one caller:
- `intraday/wiring.py:63` (intraday record);
- `intraday/feed_wiring.py:51` (feed);
- `intraday/backfill_wiring.py:46` (candles);
- `quotes/index_wiring.py:20`, one provider for the index recorders, which run one after another;
- `quotes/window_wiring.py:28`.

`groww_quiet_windows.py:3-5` also says "every scheduled routine runs in its own container, so no limiter is shared."
Fix: replace the reason with "today has no host ceiling, so adding one would be new behaviour".

**The shared per-process 429 pause: FAIL (strong evidence on the first two points, reasoning on the third).**
1. **It changes nothing today.** No process holds two `GrowwProvider`s (list above), so a per-process pause equals
   today's per-provider pause in every real run. It adds a mechanism and a named behaviour change for no present
   benefit. That breaks the repo's own rule, "never add a pattern without a second use".
2. **Its safety claim is unproven, and the repository hints against it.** "When one is rate-limited the others couldn't
   succeed anyway" holds only if Groww's limit is one aggregate per token. The code names a per-type limit: "Groww's
   300 a minute **Live Data** cap" (`groww_quiet_windows.py:3`). The plan's cited evidence,
   `research/school/probes/2026-10-22-p0-1-groww-chain.md`, is not in this repository at this SHA, so I could not check
   it. My recollection is that Groww publishes separate limits per API type (orders, live data, non-trading); that is
   reasoning only, not verified here.
3. **If the limits are per type,** a future process mixing types would have a shared pause refuse reads that would have
   succeeded. That is weaker on data. Sharing pauses across providers is exactly the "data-vs-blacklist" trade-off the
   orchestrator deferred to the owner one ruling earlier.

Fix (text only):
- R1d1 keeps **one 429 pause per `GrowwProvider`, exactly as today** (`groww.py:142`). The index recorders keep sharing
  theirs through their one provider.
- Condition 4 becomes "one pause per provider as today". The tests: two recorders on one provider share the pause, and
  two providers do not.
- A cross-provider or per-process pause goes to the owner with R1d2, together with the evidence on Groww's limit
  granularity.

**Not blocking:** the plan's "Groww 429" table row still says "the process pauses all Groww reads". Today it is per
provider, which is one per process only because each command builds one. Reword it.
