# Judge 526: MS-SIM-e1, the practice archive core

**Scope:** story/ms-sim-e1 at 51f97c73 (merged with main; builder session_01W2JE3W9xYftEDWTysHkdVC), diff from main:
`fno/school/simulator/archive/{names,archive}.py`, their tests, and story section 7.8. Lane 1 (records, outside service
later). Round 1 of 2. Judge H (session_01KNkZVoWvXMkoihKrrXk5Xa).

**Verdict: PASS**, with 4 minor notes.

## Checked against 7.8
| Item | Result | Evidence |
|---|---|---|
| Write-once, under `school-practice/` only | MET | Writes go through O9's `DataStore` (`RawFileConflict` on other bytes gives `PracticeConflict`). A path outside the run is refused before any write. Plants caught: run check removed, area renamed to `school`, conflict catch widened |
| Every line keeps the practice label | MET | The record file's `label` key is checked on every line, and every non-empty text line must start with the label. Plants (both checks removed) caught |
| Rerun idempotent or refused | MET | The remote receipt is judged first: same SHA returns the same file and no commit; other bytes give "rule broken", nothing written. Plant caught |
| Run id with `/`, `..`, empty (or anything else) refused | MET | `RUN_ID_PATTERN` fullmatch `\d{8}_\d{8}_[0-9a-f]{12}`. Plant (pattern `.+`) caught. The id follows roads, scenarios, commit and input digest; plant (inputs dropped) caught |
| No path collides with the pilot's | MET | Every pilot path is under the single `school/` area (`SCHOOL_AREA`: dashcam slot files, counts and their opportunity/marks siblings, the instructor folder), and the practice top segment is `school-practice`. The test proves it on slot files and counts over sample sessions (minor d) |
| Read-back verify | MET | `verify` compares the Drive bytes' SHA with the receipt. Plant caught |
| Gates | MET | pytest -n 6: 14,326 passed, 16 xfailed. ruff check/format, check_imports and check_records are clean |

## Minor
- (a) `archive()` checks only that the path starts with the run folder. It doesn't re-apply `file_path`'s `..` and
  empty-part checks. My run: `school-practice/<run>/../../school/x.jsonl.gz` and `.../median//x.jsonl.gz` are refused
  only by the real `DataStore` (`path_parts`, ValueError). That is safe, but the archive should check this itself,
  because e2 may hand it other stores.
- (b) "Canonical record lines" is checked only as JSON lines with the label. `{"label": "practice (simulator)"}` with
  no `record` or `type` passes. Decode each line as `decode_slot_file` would.
- (c) The story names `report.txt.gz`, but the code archives `report.txt` as plain text. Also, a non-UTF-8 text file
  raises `UnicodeDecodeError`, not `PracticeArchiveError`. Align the name with the story (or the story with the code)
  and wrap the decode.
- (d) Add the instructor folder and `opportunity_path`/`marks_path` to the collision test's sample, so "every pilot
  path function" is literal.

## Plants
9 planted, 9 caught.
