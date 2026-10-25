# Judge 626: MS-P0b story text, market school capture probes at a study pace (story/ms-p0b-capture at 412ff59cd)

**FAIL, lane 1.** Round 1 of 2. Judge I, own session (session_01CHtddAzFcEdQh4HFiz3mqU), 25 Oct 2026. Text only
(`docs/stories/MS-P0b-capture-probes.md`). Judged by reading, against the code and decisions on `main`.

## Checks asked for

| Check | Verdict | My evidence |
|---|---|---|
| The owner's decision recorded as theirs | MET | Section 1 quotes DESK_DECISIONS line 344 ("fetch it, store it ... read it as a study pace"); probe 2's terms finding kept on record |
| Budgets and gaps enforced in code | MET | Counts: 6+4+40 = 50 a slot × 4 + 6 = 206 Groww; 6+4+1 = 11 × 4 = 44 NSE. Caps of 240 and 50 counted across reruns (counts file); `StudyPace` 1.0 s / 3.0 s; criteria 1-2 with fake clocks and boundaries |
| Stop rules end the source for the day | PARTLY | 429 (Groww: first; NSE: second), 403 and an empty 200 are covered (criterion 3). Finding 1 |
| One sign-in per run; a failed sign-in kept | MET | Section 3 and criterion 4. The per-call retry it cites is real: `GrowwProvider.api` re-signs in whenever `_api` is None (`groww.py:139-145`) |
| Honest User-Agent, never a browser string | MET | Section 3 and criterion 7 (Mozilla/Chrome/Safari fail) |
| Read-only Groww through the unchanged allow-list | MET | `get_quote`, `get_option_chain` and `get_expiries` are in `READ_CALLS` (`fno/intraday/read_only.py:13`); criterion 6 (import closure, no `GrowwAPI`) |
| Clear of the v4 timeline and A16's marks | MET | Slots 10:07, 11:37, 13:07 and 14:07, a hard stop at +6 min (2 min before the next mark), at <=60 Groww calls a minute. The blackout days are a named constant; criterion 5. The 14:07 slot overlaps only the routine's set-up; A14c's margin check reads no Groww (`fno/checks/validity_margin.py`, no provider) |
| Write-once Drive with receipts | MET | Section 5 and criterion 9 (O9 `DataStore`, `RawFileConflict`, no receipt on a failed write) |

## Findings

1. **Should-fix: the stop rules leave the most likely NSE refusals undefined.**
   - Section 3 names 429, 403, an empty 200, and 5xx or a timeout.
   - It does not name a 401, 404 or other 4xx, or a 200 whose body is not JSON. NSE's `/api/` endpoints answer a
     request without a valid session cookie with 401 **[some evidence: widely seen behaviour; not measured here]**.
     A block page can come as HTML with status 200 **[reasoning only]**.
   - Under the text as written, such answers are neither a stop nor a retry, so the probe would keep calling a source
     that refuses it. That is the opposite of the owner's "do not bombard it".
   - Fix expected: "any 4xx other than 429, and any 200 that is not the expected JSON (empty or not), stops the source
     for the day", in section 3 and criterion 3, with tests (401, 404, an HTML 200) and a plant.

## Notes (not findings)

- Groww's errors come through the SDK, not as HTTP statuses. Say how a Groww 429 or 403 is recognised: A16 already
  has a rule (`fno/intraday/feed_probe.py:175`, the exception's `code` "429"). Reuse it, never a second copy (DRY).
- The cap counts live in a committed counts file. A run that dies before its commit leaves that day's count
  uncounted for a rerun. Say whether the count is written before each request or only at the end.

## Gates

Doc-reading tests at 412ff59cd, with `FNO_SLACK_BOT_TOKEN` kept: 922 passed, 14 xfailed; record scan clean.

## Addendum 1: round 2 at 9fcb60682 (diff 412ff59cd..9fcb60682)

**PASS, lane 1** (Judge I, own session). The diff changes only `MS-P0b-capture-probes.md`.

| Item | Verdict | My evidence |
|---|---|---|
| 626.1 should-fix | FIXED | Section 3: any other 4xx (401, 403, 404, ...) and any 200 that is not the expected JSON (empty, HTML, wrong shape) stop the source for the day, with no retry. Criterion 3 tests 401, 403 and 404 each, and the three non-JSON forms; its plant (the rule narrowed to 403) must fail the 401 test |
| Note: shared 429 detection | FIXED | `_rate_limited` exists at `fno/intraday/feed_probe.py:174` as cited. It moves to one shared public function that both import, adding the SDK's `GrowwAPIRateLimitException` form, with a test for each form. Editing A16h's file is limited to the import, and the orchestrator confirmed it |
| Note: when the cap is counted | FIXED | Before a slot's first request, a reservation of the whole slot budget is pushed. It is replaced at the slot's end, and a reservation with no end counts as fully spent. A failed reservation push starts no request (fails closed). The plant: a run killed after 3 requests reruns with the full reservation counted |

Note for the code round: the reservation adds a push before each slot, so up to 8 pushes a day to `main`. Each push
must stay within the story's own paths (criterion 11).

Doc-reading tests at 9fcb60682, with `FNO_SLACK_BOT_TOKEN` kept: 922 passed, 14 xfailed; record scan clean.

The head moved to 073b8b9e7 after this addendum: one sentence records the orchestrator's ruling that there is one 429
detector for the project, owned by the Groww rate-safety builder (`GrowwRateLimited`), and that P0b imports it. It is
consistent with the note above, and nothing else changed (`git diff 9fcb60682 073b8b9e7`: 3 lines in
`MS-P0b-capture-probes.md`). **PASS holds at 073b8b9e7**; doc-reading tests there: 922 passed, 14 xfailed.
