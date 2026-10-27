# Judge 35: R1d plan, Groww pacing (judge #2)

Branch `story/R1d-plan`, SHA `d3cab04e19a4c834ce89f6079682ae0eaabf7db3`, text only. **FAIL** (round 1) on 2 should-fix.
The design choices are never weaker than today: each caller keeps its limiter, there is no host ceiling, and there is
no Groww probe. But the two reasons the plan gives for them are not what the code shows, and the owner's later ceiling
decision would rest on the first one.

## What I checked in the code (`main`)

| Claim | Code | Verdict |
|---|---|---|
| Intraday 4/s | `intraday/groww_source.py:36` `WORKERS, PER_SECOND = 4, 4`; `RatePacer(PER_SECOND)` at `:56` | MET |
| Candles 0.5 s, one at a time | `intraday/candle_source.py:18` `MIN_GAP_SECONDS = 0.5` | MET |
| Index recorders 2.5/s with 3 workers | `quotes/indices.py:25`; one `RatePacer` per recorder (`recorder.py:127`); the recorders run **one at a time** (`indices.py:66-75`), so the combined index rate is 2.5/s | MET (the plan's condition 5 wording is right) |
| Other slots: own `per_second` or none | `quotes/slot.py:18`; `NIFTY_SLOT = Slot()` is unpaced | MET |
| Today each provider has its own pause | `providers/groww.py:139-141`: each `GrowwProvider` builds its own `GrowwSignIn` and its own `RateLimitPause()` | MET |
| No probe or half-open (condition 1) | today's pause just ends at 60 s (`groww_rate_guard.py` `RateLimitPause`) | MET |

## Findings

1. **S1 (should fix): "two callers in one process would sum to 6.5 a second (390 a minute)" is not what the code
   does, and the orchestrator relayed it as measured.** The plan computes it ("would sum"); it measures nothing. I
   found no process that holds both callers.
   - Each Groww command builds **one** provider: the intraday recorder (`intraday/wiring.py:63`), `quotes
     record-indices` (one provider shared by every index recorder, `quotes/index_wiring.py:20`), the 3 pm NIFTY
     recorder (`composition.py:53`), a named window (`quotes/window_wiring.py:28`), the candle back-fill
     (`intraday/backfill_wiring.py:46`), the feed probe (`intraday/feed_wiring.py:51`) and pre-open
     (`preopen/wiring.py:80`). The intraday 4/s and the index 2.5/s are different commands, so different processes.
   - This is some evidence (a reading of the wiring, not a run).

   So "already above Groww's 300 a minute and working" is unsupported. Per process today: intraday at most 240 a
   minute, index 150, candles 120. A per-process ceiling of 10/s and 300/min would be inert for every **paced** caller.
   The one unknown is the unpaced NIFTY recorder (1 worker, bounded only by latency).

   Dropping the ceiling in R1d1 is still right: it adds nothing and cannot be weaker. But the stated reason must be
   corrected to "no ceiling, because a ceiling is new behaviour and the unpaced recorder's peak is unmeasured". The
   owner's later decision must not be told that 390 a minute already works. If several processes overlap in time
   (the same API key, separate sign-ins), the aggregate at Groww is a cross-process figure that only logs can give;
   say so.
2. **S2 (should fix): the shared pause is lossless, but not for the stated reason.** The orchestrator relays "same-process
   providers share one Groww token, so a paused provider couldn't succeed anyway". That is not so. Each `GrowwProvider`
   signs in on its own (`groww.py:139`), so two providers in one process hold two access tokens on one API key. Whether
   a 429 on one means the other fails depends on how Groww buckets its limits (per key, per token, per API type), which
   is not known here. Groww documents separate limits by API type, and a 429 on live quotes need not stop a historical
   candle read (reasoning only).
   - The real reason the change is lossless today: **no process builds two providers** (S1's list). A shared
     per-process pause therefore changes nothing today. The index recorders already share one provider, so one pause.
   - Write that, and make the never-weaker test pin it: a test that every Groww composition root builds exactly one
     provider. The day a process gains a second provider, the shared pause becomes a real behaviour change, and that
     test must fail first, sending the question to the owner.
   - With that, I accept the shared pause as a named, test-pinned delta, excluded from the auto-revert. Without it, the
     claim "only makes the process stop sooner, never later" can hide lost reads in a future two-provider process.

## Other

- Per-caller spacings are preserved and the never-weaker tests are specified (conditions 3-5). The condition-5 test
  ("two callers in one process ... combined rate equals the sum") is fine as a test of "no ceiling", though no such
  process exists today.
- The `R1c-drive.md` line-number edits are correct (`drive_only_store.py:49-63`, `drive_session.py:44-66`), and so is the
  test-split follow-up.
- The R1d2 parking, R1d3 (`jitter 0` for the 15:40 close read) and the R1d4 ordering are sound.

**Verdict: FAIL** (round 1). Both fixes are text plus one named test; the design stands.
