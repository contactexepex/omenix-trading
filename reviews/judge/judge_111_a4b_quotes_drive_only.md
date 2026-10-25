# Judge 111: A4b raw Groww quotes in Drive only: story text at `story/a4b-quotes-drive-only` d1c2d06 (lane 1, quality rule 1)

Judge D. Scope: the A4b section of `docs/stories/A-data-foundation.md`, the A4 storage line and the plan row, at
d1c2d06f1b01539c5903671b12f1d5bad4c14674 (revision 2; ec4ace4 before it). Text only. I judge only what is pushed. The
builder's local evidence (the 14 Oct replays A-C) is a claim until it is reproduced on pushed code.

**What I checked on `main` myself:**
- `FREEZE_v3.md` lists `fno/forecast_scoring/wiring.py` under "Recorded, not byte-checked" (line 34; recorded
  `c24a4e9f...`, today `1215c5df...`).
- `FREEZE_v2.md` lists `fno/quotes/recorder.py` there too (line 79; recorded `0775c4cc...`, today `a9a06063...`).
- `forecast-capture.yml` (lines 59-62) and `forecast-scores.yml` (lines 31-34) already pass the four `FNO_GDRIVE_*`
  secrets.
- The 14 Oct quote file hashes to `9d9de08b...91ca1`, equal to its sidecar's `csv_sha256`. The sidecar's 21 keys are
  exactly the story's table (`raw_file_saved` aside).
- PROTOCOL_v3 §2's replay text.
- Owner rows "6 A", "7 A" (one more raw file today) and "8 A" (packs derived only, E2b) are on `main`.

## Rulings asked for

**1. G4's replay after A4b: the builder's reading is ACCEPTED. No G1 v3 amendment is needed. One consequence goes to
the owner.**
- PROTOCOL_v3 §2 says the replay uses "the inputs at the parent of the commit that added its pack, never from today's
  grown panel", and "exports ... the quote snapshots ... from that commit". The rule protects point in time and byte
  equality.
- After A4b, that commit still fixes the quote bytes: the sidecar's `csv_sha256` is in the commit, and the Drive copy is
  used only if it hashes to it. A different copy is refused, never used.
- The byte-frozen `replay.py` is unchanged. The changed `recompute_live_day` sits in v3's "recorded, not byte-checked"
  table, whose stated lock (the Q5 resolver test) is untouched.
- "The quote snapshots from that commit" then means the commit's snapshot records, with their bytes by pinned hash.
  The inputs, and so the outputs, are byte-identical (the builder's case B; to be reproduced on pushed code).
- **What changes is availability, not integrity.** A replay now needs the Drive copy to exist. If it is lost, that
  day can never be replayed, where git kept it for ever. The owner chose "6 A" knowing raw quotes leave git, but
  probably not this consequence. The orchestrator should tell the owner in one line (no decision needed unless the
  owner objects).

**2. `fno/quotes/recorder.py`: the pushback is ACCEPTED.**
- It is "recorded, not byte-checked, behaviour locked by the golden cases" (v2), and A7, A5 and O6 already changed it
  after passes.
- The store-only alternative is worse, as the builder shows. A raise ends `record()` with no retry and no reason. A
  swallowed error makes an attempt canonical while its file exists nowhere.
- Condition: the change is only the guarded save, plus `raw_file_saved: false` on failure. A complete attempt's files
  stay byte-identical (`test_recorder_baseline.py` unchanged), and `tools/forecast_live_golden.py` passes unchanged.
  `market_levels.py` is not touched.

**3. The 14 Oct file: `git rm` after a verified Drive copy is ACCEPTED.**
- The owner's row says it "stays in history (never rewritten)", and `git rm` keeps it at 5c22bcc.
- Every reader of that day keeps working:
  - the replay exports the pack commit's parent, which still holds the file;
  - desk meeting 2 reruns at its own commit;
  - live readers find the sidecar without `raw_file_saved`, which counts as saved, and read the hash-checked Drive
    copy.
- The routine's "never delete a recorded attempt" rule binds the routine, as the text says.

**4. `spot` in the public sidecar: noted as the orchestrator's decision, not the owner's.** It is a public index level
and no option quote, so it is acceptable (reasoning only). The record should label it as the orchestrator's decision.

## Story-text check

Correct and complete:
- the split table;
- the store design (lazy private store, hash-checked `get`, loud and distinct errors, `None` only for "no file");
- the reader table and the call-site table, the call-site table (my grep of `fno/` finds the same 8 files calling
  `build_quote_store`; the ninth row, `fno/quotes/cli.py`, reads the folder directly today, as the table says);
- Drive-down handling (never to the repository, never spooled, retry to 15:10, "none", one alert, exit 1, the error's
  type only in the public sidecar);
- the record-scan rule plus `.gitignore` plus a tree test;
- the gap list;
- the "found outside scope" items (E2b by the owner's "8 A", the forecast job now failing closed instead of falling back
  to NSE: stated for the owner).

## Should-fix

**1. Criterion 6 contradicts the design.** It says "No file in the G1 v1, v2 or v3 freeze tables changes". But the
design changes `fno/quotes/recorder.py` (v2's "recorded" table) and `fno/forecast_scoring/wiring.py` (v3's), which
rulings 1-2 accept. As written, the code would fail its own criterion, or the criterion would be read loosely. Fix: "no
**byte-checked** file of the G1 v1-v3 freezes changes; the two recorded files change only as rulings 1-2 allow, with
the golden recompute, the A4 baseline test and the Q5 wiring test unchanged and passing".

**2. The routine's Drive settings must be a merge condition, not "to be checked".** Found-outside-scope item 3 says
the 3 pm routine's environment "was not checked". If it lacks the four settings, every day after the merge ends "none":
- no canonical snapshot;
- so no G1 live pack;
- and no E2/C4/Book 1 inputs.
Quality rule 8 also requires an end-to-end run after the merge. Fix: add a criterion. Before the merge, a run in the
routine's own environment shows the Drive settings are present and a write-and-read of a test file in the raw area
works, without printing a value. After the merge, the first real 15:00 run's result line and Drive hash check go in the
log. If the settings are missing, the owner adds them first and the merge waits.

## Minor

1. `failures` holds provider exception texts in the public sidecar ("not proven price-free"). Record the exception
   type plus a fixed message, as already done for Drive errors, or add a test that no number shaped like a price
   appears in `failures`.
2. `replay_quote_store`: a pre-A4b commit's own file should also be checked against its sidecar's hash, so both paths
   share one rule.
3. Process: the orchestrator reports that the builder wrote code before this check (quality rule 1 says code starts
   after it). Its evidence counts only once reproduced on the pushed code.

**Verdict: FAIL for d1c2d06f1b01539c5903671b12f1d5bad4c14674** (story text), on should-fixes 1-2, both wording and
criteria only. Rulings 1-3 stand for the code check. A re-check needs only the A4b section.

## Addendum 1 (15 Oct 2026): story text revision 3 at 6db62600c85d8cfa4de81e2ca3edc39aa148ab35 (d1c2d06..6db6260)

One commit, which changes only `docs/stories/A-data-foundation.md` (+40 −8). Text only.

| Item | Status | Evidence |
|---|---|---|
| Should-fix 1: criterion 6 | MET | "No byte-checked file of the G1 v1-v3 freeze records changes", checked by a script over every `FREEZE*.md` byte-checked table against the diff (`replay.py` named). Only `recorder.py` (R2 and criterion 9) and `forecast_scoring/wiring.py` (R1) change. Named tests: the freeze tests, `forecast_live_golden.py`, A4's baseline (byte-identical for normal and december; for retry and none only the `failures` strings change, with their fixtures updated for exactly those strings), the Q5 wiring test, and a real 14 Oct replay from the commit's file and from Drive |
| Should-fix 2: merge condition | MET | A write-read probe through `build_quote_store` in the routine's own environment, printing only "drive write-read ok" or the error type. Rule 8's first real 15:00 run (result line, sidecar committed, Drive hash equal to the sidecar's) goes in the log and the merge record. The orchestrator's decision 14 (the merge waits for the owner's probe) matches |
| Minor 1: public failure texts | MET | New criterion 9: `<where>: <exception type> (provider message withheld)` and `raw quote file not saved: <type>`, with a planted-value test over every repository file and the result line. The cost is stated |
| R4 label | MET | `spot` stays public "by the orchestrator's decision", accepted by judge 111 R4 |
| Pushback on minor 2 (hash-check pre-A4b files in the replay) | **ACCEPTED** | A pre-A4b commit's quote file comes out of `git archive` of that commit. Git addresses blobs by their own hash, so the bytes are exactly the committed ones, and a sidecar check adds nothing there. The check would also refuse golden case A, which `test_live_replay.py:93-102` replays. One correction to the builder's wording: case A's sidecar has **no** `csv_sha256` key at all (`nifty_20261013_145600.meta.json`; the file hashes to `25a5f9ea...`), rather than a wrong one. The effect is the same: a check would refuse it or need an exception |

The A4 baseline fixtures changing for retry and none is not a loosened test. It is the deliberate output change of
criterion 9, with the normal and december cases still byte-identical. The code check will confirm that only those
`failures` strings differ.

**Verdict: PASS for 6db62600c85d8cfa4de81e2ca3edc39aa148ab35** (story text). Code may start. The merge also needs the
owner's routine-environment probe (merge condition; decision 14).

## Addendum 2 (15 Oct 2026): the code at 65d75e63c6626bf5e359b961b36eaf3f7215b1b5

The code commit is 3ac5e65 (parent 6db6260, the passed text); efd71d0 merges `main`; the last two commits touch
response 111 only. I judged A4b's own diff (`git diff 3ac5e65^ 3ac5e65`) and ran everything on the merged tip.

## Gates

- Full suite at 65d75e6: **3,591 passed** (Slack token unset). `ruff check`, `ruff format --check` and `check_imports`
  are clean. A trial merge with today's `origin/main` conflicts only in `reviews/claude/README.md` (index rows on both
  sides; keep both).
- **Frozen files.** Of the files A4b changes, only `fno/quotes/recorder.py` (FREEZE_v2, recorded) and
  `fno/forecast_scoring/wiring.py` (FREEZE_v3, recorded) appear in any freeze record, as rulings R1 and R2 allow. No
  byte-checked file changes.
- **A4 baseline fixtures.** Only `retry/.../nifty_20261013_145503.meta.json` (1 line) and
  `none/.../nifty_20261013_150933.meta.json` (12 lines) change, and only their `failures` strings: `ConnectionError:
  dropped` becomes `ConnectionError (provider message withheld)`. No other fixture changes.

## Real checks, on real data (read-only)

- **The 14 Oct Drive copy.** Read through the committed `build_quote_store()`: 67,154 bytes, SHA-256 `9d9de08b...`,
  equal to its sidecar's `csv_sha256`, read in 2.5 s. No Groww `.csv` is tracked in the tree.
- **Replay of 14 Oct from git.** `python -m fno forecast-scores replay --day 2026-10-14`: "reproduces; inputs from
  73ec163dc3, pack from c46f64c5e3".
- **Replay of 14 Oct from Drive.** The same replay with the Groww CSV deleted from the exported inputs: pack and
  records equal (`matches: True`).
- **The O5 rule in a scratch worktree with the hooks on.** A CSV under `research/data/quotes/groww/` is ignored by
  git. Added with `git add -f`, the commit is refused: "raw Groww quote file (Google Drive only, story A4b)". The same
  holds for an upper-case `.CSV`. Nothing was committed.

## My mutations: 15 of 15 caught

| Plant | What it would break |
|---|---|
| A1-A3 | the hash check is skipped; `raw_file_saved: false` is ignored; a missing Drive copy returns a quiet `None` |
| A4, A6 | a failed save does not make the attempt incomplete; the sidecar flag is not written |
| A5 | the provider's message is written into `failures` (criterion 9) |
| A7 | NSE's CSV is sent to Drive |
| A8, A14 | the scan's suffix check becomes case-sensitive; the forbidden-files rule is removed from the scanner |
| A9 | E3's capture commits the CSV |
| A10 | E4's Drive read error does not become `SnapshotError` |
| A11 | the replay always reads the local folder |
| A12, A13 | the exit code ignores a raw-file error; the raw-file alert is not sent |
| A15 | the Drive store is built eagerly (it signs in without need) |

## Criteria

| # | Result | Evidence |
|---|---|---|
| 1 Raw rows to Drive only | MET | `DriveOnlyQuoteStore.put`. A1/A7 plants. The 14 Oct Drive copy verified |
| 2 No raw quote in the repository | MET | `.gitignore`, the O5 rule (my real commit attempt refused), no tracked Groww CSV, the 14 Oct file `git rm`'d with its sidecar and marker kept |
| 3 Hash-checked reads, loud failures | MET | A1-A3 |
| 4 Every reader keeps working | MET except the replay case below | Readers and call sites tested (`test_drive_only_readers.py`); `quotes report` and `compare` read through the store; E3 commits only repository files (A9); E4 gives `SnapshotError` (A10) |
| 5 Drive down | MET | No `.csv` anywhere in the repository, never canonical, "none" at 15:10, one alert, exit 1 (A4, A6, A12, A13) |
| 6 Frozen files; point in time | MET | Above. Both real 14 Oct replays reproduce |
| 7 Routine text | MET | `CLAUDE.md` steps 2 and 4 name Drive, the sidecar and marker and the third alert. `quote_wiring.py` is listed as a composition root |
| 8 Gates; no credential in output | MET | Above |
| 9 Fixed public failure texts | MET | `withheld()`. A5 plant. Only the two expected fixture strings change |

## Should-fix

**1. `replay_quote_store` decides by the whole folder, not per file, and gives a false "DIFFERS" in the transition.**
- It returns the plain local store if **any** Groww CSV exists anywhere in the exported tree
  (`wiring.py:113-120`). Otherwise it returns the Drive store.
- The owner's "7 A" lets today's routine commit one more raw CSV (15 Oct) before the merge, and the orchestrator plans
  to remove it in a follow-up. Every live day captured while that file is still in the tree is replayed with the local
  store.
- The day's own CSV is in Drive only, so `load_snapshot` (frozen) finds no Groww file. It silently moves on to NSE's
  snapshot, and the replay reports a mismatch for a correct live day.
- Reproduced: the 14 Oct export with its CSV removed and a 13 Oct CSV left in the tree. The local store was chosen,
  and `pack.json` and `forecasts.csv` both differ.
- Fix: choose per file. If the export holds that quote file, use it; else read it from Drive, hash-checked. My
  accepted pushback on minor 2 still holds for files that come from the commit. Add a test of the mixed tree.

## Minor

1. `levels_failures` in the public sidecar still carries NSE exception messages (`market_levels.py:83,87`: `india vix:
   {type}: {exc}`). This is NSE's public data, not Groww's, and outside criterion 9's `failures`. Applying the same
   withheld form would be consistent.
2. Merge condition, unchanged: the owner's write-read probe in the routine's environment (decision 14), then rule 8's
   first real run logged. A 15 Oct raw CSV committed before the merge needs its verified Drive copy and `git rm`, which
   should-fix 1 makes safe either way.

**Verdict: FAIL for 65d75e63c6626bf5e359b961b36eaf3f7215b1b5**, on should-fix 1 only. Everything else is verified on
real data and with 15 of 15 mutations caught. A re-check needs only `replay_quote_store` and its new test.

## Addendum 3 (15 Oct 2026): the replay fix at fe0f5cc120ba4408af4d01e7e670ddc603230bf6 (65d75e6..fe0f5cc)

A4b's own change is e5d4ff0. ba6a2e8 merges `main`, and fe0f5cc touches response 111 only.

| Item | Status | Evidence |
|---|---|---|
| Should-fix 1: per-file replay store | MET | `ExportFirstQuoteStore` (25 lines) returns the export's file when present (bytes from `git archive`), else the Drive-only store, which is hash-checked and loud. It never writes (`ReadOnlyStoreError`). `replay_quote_store` builds it |
| My reproduction re-run on real data | MET | The 14 Oct export with its CSV removed and a 13 Oct CSV left in the tree now gives `pack.json` and `forecasts.csv` equal, `matches: True`. The plain 14 Oct replay from git also gives `matches: True` |
| Tests bite | MET | My plant "always the Drive-only store" (export ignored): 2 tests fail. The builder's mixed-tree test and the export-only test, which asserts Drive is never asked, are present |
| Frozen files | MET | Of A4b's changes, only `fno/forecast_scoring/wiring.py` (FREEZE_v3, recorded; ruling R1) appears in any freeze record. Other `fno/` changes in the range come from the merge of `main` |
| Minor 1 (`levels_failures`) | Not taken, orchestrator's decision 20 | Acceptable: NSE public data, outside criterion 9 |

**Gates on fe0f5cc:**
- **3,702 passed** (Slack token unset).
- `ruff check`, `ruff format --check` and `check_imports` are clean.
- A trial merge with today's `origin/main` conflicts only in `reviews/claude/README.md` (index rows; keep both).

**Verdict: PASS for fe0f5cc120ba4408af4d01e7e670ddc603230bf6.** The merge condition stands (orchestrator's decision 14):
1. The owner's write-read probe in the 3 pm routine's environment must pass first, printing only ok or an error type.
2. Merge with both index rows kept, and run the full suite on the merged tree.
3. Rule 8: log the first real 15:00 run (result line, sidecar committed, Drive hash equal to the sidecar).
4. Any raw 15 Oct CSV committed before the merge gets its verified Drive copy and a `git rm`. After this fix that is
   safe for replays at any point.

I check the merge commit after it lands.

## Addendum 4 (15 Oct 2026): the delta fe0f5cc..1e159ef (a merge of main that moves today's raw file to Drive)

**Verdict: PASS.**

**What the merge changes beyond a plain merge (my check).** `git merge-tree --write-tree fe0f5cc fe695ef` gives the
clean merge tree. Against it, 1e159ef differs in exactly two places:
- it deletes `research/data/quotes/groww/derivatives/quote-snapshots/2026/10/nifty_20261015_150225.csv`;
- it resolves the `reviews/claude/README.md` conflict by keeping A4b's Response 111 row.

Nothing else is touched. The file's `.meta.json` and `nifty_20261015.canonical` stay.

**The deleted file is safe in Drive (three hashes, all mine).**
- **The git blob being removed** (in main parent fe695ef, "O6 Actions: NSE 3 pm quotes 2026-10-15"): SHA-256
  `9cd78698…e0bd672`, 67,092 bytes.
- **The sidecar** `nifty_20261015_150225.meta.json` at 1e159ef: `csv_sha256` `9cd78698…e0bd672`; 184 expected and 184
  recorded contracts.
- **The Drive copy**, read read-only through A4b's own `build_quote_store()` (a `DriveOnlyQuoteStore`) with this
  session's Drive credentials: 67,092 bytes, SHA-256 `9cd78698…e0bd672`.

All three are equal, so the recorded attempt is not lost: it moved to its A4b home and its record stays in git.

**Gates on 1e159ef, run by me.** 5,596 passed with `FNO_SLACK_BOT_TOKEN` unset. ruff and check_imports are clean.
`tools/check_records.py`: "record scan: clean (5902 files)".

**Rulings.**
1. **The deletion inside the merge commit: accepted.**
   - A4b's record scan refuses any staged tree holding a Groww `.csv`. Committing the merge first and deleting second
     would need `--no-verify`, which is never allowed.
   - Folding the deletion into the merge is the only compliant path. The diff against the clean merge tree above shows
     exactly what the merge adds, so nothing is hidden.
   - Decision 36 governs account commits, not a story branch's merge.
2. **The Slack refusal alert from the first attempt: no finding.** It is the hook doing its job (file and kind only, no
   values).
3. **Said plainly, not a finding:** the raw file stays readable in git history (commit fe695ef on `main`), as the 14
   Oct file did. A4b stops new raw files reaching the repository; it cannot remove past history without rewriting
   `main`, which the project never does. If the owner wants the history cleaned, that is a separate, deliberate
   decision.

**Merge and rule 8.** The merge waits for main's unrelated E1b test fix, with a full suite on the merged tree. Rule 8
is tomorrow's first 3 pm run: the sidecar and `.canonical` committed, no raw `.csv` in git, and the Drive copy's
SHA-256 equal to the sidecar's `csv_sha256`. I check it then. The owner's probe ("drive write-read ok" in the routine's
environment) meets my earlier merge condition.

## Addendum 5 (15 Oct 2026): merge check, A4b merged to `main` as 3a0ffa8f

**Merge structure: complete and matching the PASS. Rule 8: open until the 16 Oct 3 pm run.**

- **The merge commit.** The orchestrator named 2355b80b, but that is the next merge (C5b). The A4b merge is its first
  parent, `3a0ffa8f`, whose parents are `f0ad466f` (main) and `1e159ef`, the SHA I passed. It is on `origin/main`.
- **Same change.** Its tree equals the clean `git merge-tree` result of those two parents: no change made in the merge.
  Every file A4b changed that main did not touch is byte-identical to 1e159ef.
- **No Groww raw file under `research/data/quotes/`** on main. The only tracked `quotes/groww/…csv` files are three
  test fixtures outside it:
  - two G1 v2 golden cases (17 lines each, with different content);
  - one C3 test fixture (5 lines).

  A real 3 pm capture has about 180 contracts, so these are small hand-made fixtures, not captures (reasoning from
  size and content hash). The A4b scan rule rightly covers only `research/data/quotes/groww/`.
- **Gates.** The orchestrator reports 5,761 passed on main, the record scan clean (5,927 files) and CI green. I did
  not re-run these here; my own gates ran on 1e159ef (addendum 4) and the merge adds nothing to it.
- **Rule 8 (open).** The 16 Oct 3 pm run must commit only the `.meta.json` sidecar and the `.canonical` marker, no raw
  `.csv`, and the Drive copy's SHA-256 must equal the sidecar's `csv_sha256`. I check that run.

## Addendum 6: rule 8, the live 3 pm run of 16 Oct 2026 (Drive only for Groww's raw rows)

**PASS.** I checked commit 2ec7c6e6, "3 pm quotes 2026-10-16 (Groww + NSE)", pushed 15:05 IST by the scheduled
routine. The Drive check was read-only, and no quote value was printed or stored.
- **Repository:** under `research/data/quotes/groww/` the commit adds only `nifty_20261016_145500.meta.json` and
  `nifty_20261016.canonical`. `git ls-files` finds no Groww `.csv`, and `.gitignore:26`
  (`research/data/quotes/groww/**/*.csv`) covers the path. The NSE part commits its own public chain CSV, as
  designed.
- **Drive equals the sidecar:** the Groww file `groww/derivatives/quote-snapshots/2026/10/nifty_20261016_145500.csv`,
  read through the raw area, hashes to the sidecar's `csv_sha256` (9f6f60f4…) and holds 188 rows (sidecar: 188
  expected, 188 recorded, `failures` empty, `complete` true, `in_window` true, 14:55:00-14:57:53 IST).
- **NSE:** `complete` true, 188 of 188, 14:55:00-14:55:24 IST, and its CSV hashes to its sidecar's `csv_sha256`.
  Its canonical is `nifty_20261016_145500`, as is Groww's.
- **The parts together:** both started at 14:55:00, and their spots agree within 1.5 points (Groww 23,102.3, NSE
  23,103.8). Both canonical markers name the same attempt.
- **A4c may merge** (its merge condition, judge 160 and addendum).
- **From my check-in's list:** NSE's canonical is complete today, where 14 and 15 Oct were "none". The two parts went
  out in one commit at 15:05 IST, before 15:13, because the per-part commits are A4c's change and A4c is not merged
  yet. That is today's expected behaviour, not a finding. Once A4c merges, the next live day should show one commit per
  part, NIFTY first (judge 160).
