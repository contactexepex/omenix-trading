# Judge 280: G7's `pack_sha256` column (story/g7-pack-sha-column at fe89e915)

Judge B, 16 Oct 2026. Lane 1 (forecast records), point 4 of G10 part 2's text (judge 274 addendum 1). Builder: R2/G7.

**Verdict: PASS.**

| Claim | Result | Evidence |
|---|---|---|
| The column sits right after `inputs_sha256` | MET | `Record` field order, and `COLUMNS` from `fields(Record)` |
| `record()` checks the form only: empty or 64 lowercase hex | MET | `PACK_SHA256 = (|[0-9a-f]{64})`, `fullmatch`; whether it is the released pack is the `fno/v4_pack` guard (judge 277). My plant (accept uppercase) fails 1 test |
| Tolerant read: a file without the column reads as empty, and a same-day write adds nothing | MET | `read()` defaults `pack_sha256` to ""; `same_as` against a new empty row is true. My plant (drop the default) fails 3 tests |
| Every committed v4 CSV still reads; no file is rewritten in this commit | MET | G7's 14 files and M1's 2 (test); the diff touches no CSV |
| No method hash moves | MET | `records.py` is in neither G7's `METHOD_FILES` (`series`, `baselines`, `rules`, `vix_rule`, `capture`) nor M1's list (checked in judge 274 addendum 1); G7's hash-gate test passes |
| No other direct `Record(...)` constructor would break | checked | grep: rows are built through `records.record` or `Record(**row)` in `read()` |

**Note:** a file's next write rewrites it whole with the new header and empty values. Readers that select columns by
name (G8's `ForecastFiles`) are unaffected. A reader that selects by position would need checking, but none was found
in this repository.

**Gates (run by me on fe89e915 merged with current `origin/main`):** 7,710 passed, no failures. `ruff check`: clean.
`ruff format --check`: 1,388 files already formatted. `check_imports`: clean.
