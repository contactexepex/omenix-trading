# Judge 33: R1d4 step 0 characterization, a lane-2 check for the orchestrator (judge #2)

Branch `story/R1d4-characterization`, SHA `e5ea34d15c39897f707f256dd0be17f3543bb074`. This is not a formal judge round:
the orchestrator asked one question, whether the 19 tests pin what the code does today. **PASS**: every assertion
matches the code. Two notes for the R1d4 refactor follow.

**Tests only:** `git diff --stat 60ab2d8 e5ea34d` changes only judge files, number CSVs and
`tests/characterization/test_global_cues_and_preopen_behaviour.py` (the branch sits on merged R1c, `0105190`). No
`fno/` change. 19 passed (`__pycache__` cleared).

## The pins against today's code

| Pin | Code that does it | Match |
|---|---|---|
| A block on 401/403/429, one request | `yahoo_source.py` `BLOCK_STATUSES = (401, 403, 429)`; `download` raises `YahooBlocked` | yes |
| A redirect is a block, not followed | `session.get(..., allow_redirects=False)`; `response.is_redirect` -> block | yes |
| A page, or Yahoo's JSON error, is a block | does not start with `{`; no `"chart"` in the first 200 bytes | yes |
| 5xx raised as `HTTPError`, no block, one request | not in `BLOCK_STATUSES`, so `raise_for_status()` raises and the gate is not set | yes |
| A dropped connection is raised, not retried | `download` has no loop; the collector (`collector.py:83-88`) and `PreopenReader.read` (`preopen.py:147`) do not retry | yes |
| One block stops every Yahoo cue, no request | `YahooGate.blocked` is checked before the GET | yes |
| Stale window | `preopen.py:39` `STALE_AFTER = timedelta(minutes=20)`; `level_status` at `:75` | yes |
| Live / stale / closed / lunch | `level_status`: another local date -> closed; `at_lunch` -> lunch; else by age. Tokyo lunch is 11:30-12:30 (`markets.py:29`); the test's 11:45 is inside it | yes |
| No session data, changed layout keep the bytes | `_archive` at `preopen.py:149`, before parsing | yes |
| Block: one request, nothing archived, no row | the block raises in `download`, before `_archive` | yes |
| Drive failure: no row, no snapshot-log row | `_archive`: `archive.put` before `log.append`, and `_append` comes after | yes |

## Plants (mine; each restored)

`STALE_AFTER` 20 -> 60: 1 failed. 429 removed from the block list: 3 failed. `allow_redirects=True`: 1 failed. The
pre-open archive put removed: 4 failed. The gate not set on a block: 1 failed.

## Notes for R1d4 (not blocking this floor)

1. **The stale window is pinned loosely.** `STALE_AFTER` 20 -> 39 also fails (the level time appears to sit one 5-minute
   bar after the stamp: some evidence, from that plant only). The two tests, at 7 and 40 minutes, still let a change
   to roughly 30 minutes pass unseen. If R1d4 touches the window, add a pair at 19 and 21 minutes of age.
2. **The floor does not cover the pacing layer.** In production, both Yahoo paths use `PacedSession`
   (`global_cues/wiring.py:280-283`), so every Yahoo answer also goes to `SHARED_PACER.observe` for its host, where a
   refusal counts toward that host's pause. These tests use a scripted session and pin `download` alone. The pacer's
   own behaviour is pinned elsewhere (`tests/characterization/test_pacer_and_public_behaviour.py`, host-agnostic).
   R1d4 must keep Yahoo on the paced session, or name the change; a test that the wiring builds a `PacedSession`
   would lock this.
