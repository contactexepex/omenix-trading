# Judge 535: receipt-bisect, the push-receipt search by halving (story/o-receipt-bisect @ 74eb7e99)

Judge F. Round 1 of 2. Lane 1 (the health check's push-time evidence; the health workflow's 15-minute limit). Labels:
**strong**, **some**, **reasoning only**.

## Verdict: PASS. It may merge before tonight's health run. 1 minor.

Gates on 74eb7e99: **14576 passed, 0 failed**, 1 skipped, 16 xfailed; ruff, ruff format (2333), `check_imports.py`
and the record scan (8806) are clean.

Why the halving is safe [strong: code read]:
- `ActivityLog.since` returns pushes **oldest first** (sorted by time), and on plain fast-forward pushes "`after` holds
  the commit" turns true once and stays true.
- Any push the method returns has passed the exact check (`before` lacks the commit, `after` holds it). On one
  fast-forward line only one push can pass it, so a returned time is never wrong. Every other outcome is "no receipt"
  or `ReceiptUnknown`.
- A window with any `force_push` (or any other activity type) is read push by push, as before.
- `low == 0` with `before` already holding the commit returns `None`. The old loop gave the same result there, ending
  in NotFound or OutsideLog.

## Plants (each reverted)

| # | Plant | Caught |
|---|---|---|
| 1 | a force-push window halved too | yes, 1 failed |
| 2 | no exact check on the found push | yes, 1 failed |
| 3 | a contradiction mid-window returns no receipt silently | yes, 1 failed |
| 4 | an off-by-one in the halving (`high = middle + 1`) | the tests hang (an endless loop): loud, not silent |

## Minor

**Two pushes in the same second [reasoning only].** `sorted(..., key=_moment)` is stable on the page's newest-first
order, so two same-second pushes come out newest first. The halving can then land past the true push, and the exact
check turns that into `ReceiptUnknown`: a lost receipt, never a wrong time. Sorting with a second key (the page order
reversed) would remove even that. Such pushes on `main` are rare.

After the merge (quality rule 8): tonight's health-workflow duration against its 15-minute limit, and its receipts
agreeing with the push-by-push search (15 of 15 in the claims).

## Addendum 1: same-second pushes (story/o-receipt-same-second @ cc33cae4)

**Verdict: PASS. It may merge** (after tonight's run, as the orchestrator set).

- The builder measured the whole live log first: 3,929 entries since 11 Oct, 12 seconds with more than one entry, all
  12 being one push logged more than once. My minor's case (two different pushes in one second) had not happened
  yet. The measurement is the builder's [some].
- The fix sorts by `(time, GitHub's activity id)` (`_order`, `fno/ai/activity_log.py`). This is better than my
  "reversed page order": it does not trust page order. The builder found the id rising strictly across all 3,929
  entries. Fakes without an id keep their old order.
- Checks:
  - my plant (sorting by time alone) fails the new same-second test;
  - tests/ai and tests/health: 239 passed;
  - the full suite: **14577 passed, 0 failed**; ruff format, imports and the record scan (8809) are clean.
