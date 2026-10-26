# Judge 29: R1c the Drive session onto the shared layer, story text (judge #2)

Branch `story/R1c-drive-plan`, SHA `441f66c663711ce2564e3ead357769801d61b619`, story only (plus the in-place R1
amendment). **FAIL** (round 1), lane 1, on 2 should-fix. The scope table matches `drive_session.py`, the
no-Drive-breaker ruling is sound, and the invariant holds on every write path I traced. One "stated difference" makes
fewer attempts at the Record store than today.

## Criteria

| Item | Verdict | Evidence (`main`) |
|---|---|---|
| Scope table vs today | MET | `drive_session.py:12-16,41-62`: `RETRY_WAITS (2, 8, 30, 60)`; `TRANSIENT {429, 5xx}`; 403 with the rate-limit reasons; `ConnectionError`/`Timeout` retried; one 401 re-sign inside the iteration, not counted; `accept` statuses returned |
| No Drive breaker; the R1 amendment | MET (I agree) | no breaker exists today, so none is not weaker. A breaker on the one write target would defer every workflow's writes together; Google's own 429, rate-limit 403 and `Retry-After` plus bounded backoff cover throttling |
| The invariant on every write path | MET by code order (tests required) | see S2 for the full list I traced |
| Stated difference 1 (jitter 0.25, upward) | MET | never shorter |
| Stated difference 2 (`Retry-After` > 120 s stops the call) | NOT MET | S1 |
| Worst-case section | MET (honest) | 400 s to 425 s per failing call; a total outage already passes the 15-minute timeouts today |

## Findings

1. **S1 (should fix): "`Retry-After` above 120 s stops the call" is weaker than today for data.** Today the header is
   ignored, and a throttled call is still retried after 2, 8, 30 and 60 s: five tries in all. The story would end
   that call at its first answer. On Drive that means a Record or receipt write not done this run, where today one of
   four more tries could have succeeded. Fix, never weaker on both axes: honour `Retry-After` as a floor **capped at
   the ceiling** (wait `min(max(t_n, Retry-After), 120)` s) and keep the same number of tries. That is more polite than
   today, which retries at 2 s regardless, and makes no fewer attempts. The worst case stays 4 × 120 + 5 × 60 = 780 s,
   as computed. (NSE keeps its rule: there, a long `Retry-After` from a source is a block signal.)
2. **S2 (should fix): name every write path and its order; the story lists five and marks some unchecked.** I traced
   these (all satisfy "no row or receipt without the file"):
   - **Record:** `FingerprintingStore.put` stores, then `manifests.record` (`manifest_folder.py:106-109`).
   - **Data files:** `DataStore.put` writes to Drive, then `receipts.write` (`data_store.py:40-46`).
   - **Revisions:** `RevisionArchive.capture` writes the bytes, then `index.append` ("bytes first: a row always has its
     file", `revisions.py:142-143`); the revision sink goes through it.
   - **Receipt repair:** `ReceiptRepair.receipt_for` reads the Drive file and refuses if there is none or several;
     `write` follows (`receipt_repair.py:27-47`). **Missing from the story's list.**
   - **Index files:** `DriveIndexStore.replace` updates the file in place with no receipt (`index_store.py`). A retried
     update of the same bytes is harmless; say so.
   - **Staging:** `StagingArea.stage`: no row or receipt.
   - **Folder and file creates:** a reserved ID plus `409 fileIdInUse` makes a retried POST safe
     (`google_drive_upload.py:53-67`).

   Fix: list all seven with these references, and give the one test per path that the story already requires, for the
   ones that write a row or receipt (Record, data files, revisions, receipt repair).

## Notes

- Claim 7 (every store method reaches `DriveSession.request`) is the right guard against a second retry loop.
- R1-resilience.md's amendment is consistent with the ruling and turns judge 1's requirement into the invariant.

## Addendum 1: round counting (orchestrator ruling, 26 Oct 2026)

`441f66c` was retracted as incomplete while this review was in flight, so the verdict above is **advisory** and does
not count toward the two-round limit. The complete superseding SHA starts round 1. S1 (the `Retry-After` wait capped at
120 s, keeping all the tries) and S2 (every write path, with `receipt_repair`) are the checklist for it.
