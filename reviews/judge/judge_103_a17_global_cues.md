# Judge 103: A17 global cues: `story/a17-global-cues` 9b6515079cd55fea1d9fb97b4e9a022f1cb34ccc (lane 1, response 103 with addendum 1)

**What I did:**
- read the story text at this SHA (criteria 1-9 and the gap list), response 103 with addendum 1, the owner rows
  (a927390 and "2 => A", superseded), and every module of `fno/global_cues/`;
- ran the gates on the exact SHA and on a trial merge;
- ran `global-cues verify` against the owner's Drive (read-only);
- read the private tables from Drive **into memory only**, to search the repository for their values;
- fetched the Treasury's 2026 file and the terms pages myself;
- probed `value_for` on US holidays, daylight-saving changes and both cutoffs;
- planted 10 mutations in a separate worktree.

I did not run `fill` or `adopt`: both write to Drive and to the repository.

## Gates

- **Exact SHA:** full history, Slack token unset: **3,263 passed**. `ruff check`, `ruff format --check` (731 files)
  and `check_imports` (741 files) are clean.
- **Trial merge with `origin/main` d942638 (now holding A15 and T1): 3,640 passed**; ruff, format (788 files) and
  imports clean.
- **Merge note:** 5 files conflict, all because A15's and T1's merged lines sit in the same places:
  - `fno/cli.py`: the `global-cues` import and parser line;
  - `CLAUDE.md`: the composition-root list;
  - `docs/stories/A-data-foundation.md`: the A15 and A17 sections;
  - `fno/storage/README.md`;
  - `reviews/claude/README.md`.

  Keeping both sides resolves each one. That is what I tested.
- Largest file: `other_sources.py`, 137 lines.

## Private values: none in the repository (the orchestrator's first point)

- From Drive (in memory): sp500 has **4,977** rows (2007-01-03 to 2026-10-14, `backfilled` and `live`), nasdaq100
  **5,059** (2007-01-01 to 2026-10-13). These are the counts addendum 1 states.
- **Every line added by every branch commit** (`git log -p 032665a..9b65150`) holds **0** of their values with 5 or
  more digits, compared as exact number tokens. This covers code, fixtures, tables, checks, manifests and response 103.
- Across the whole tree, some exact-token matches exist, but only in older files that predate this branch:
  `research/2026-10-12-capacity-screen/screen.csv`, `contracts/.../blocks-33-34.json`, weekly-weather `trades.json`
  and NSE fixtures. They are coincidences between NIFTY-scale numbers, not S&P 500 or Nasdaq 100 rows.
- The repository holds only the copy logs: `research/data/manifests/global-cues/sp500.csv` and `nasdaq100.csv`, two
  rows each with path, URL, SHA-256 and size. No `sp500.csv` or `nasdaq100.csv` table and no private row exists in
  `revisions` or `gaps.csv`; `test_no_private_cue_has_a_table_or_values_in_the_repository` pins this.
- The test fixtures use made-up values; `verify` prints "values differ (private cue: values never printed)".

## Per criterion

| # | Criterion | Builder's claim | My own evidence (positive / negative / boundary / empty) | Result |
|---|---|---|---|---|
| 1 | Publisher, URL, time zone, publication time, terms with labels; restricted sources only under an owner decision; refused sources named with alternatives | README table, source classes | I read the terms pages myself. **EIA:** "U.S. government publications are in the public domain and are not subject to copyright protection" (eia.gov/about/copyrights_reuse.php). **Cboe** (cboe.com/legal): "... reproduced, or distributed in any form or by any means, or stored in a database or retrieval system, without the prior written permission of Cboe". **Nasdaq** (nasdaq.com/legal): "Not access or use the Service, or any process, whether automated or manual, to capture data or content from the Service". All three match the README quotes word for word. The restricted sources are used only under row a927390 (personal research, Drive only, one download a day, no display), and the README says so. FRED, S&P DJI, NSE currency and MCX are named as refused, with the alternatives used | MET |
| 2 | `first_seen_at` on every row; `backfilled` vs `live` by the first NSE open after the value date | `table.provenance`, committed recompute test | Committed: 2 public `live` rows (us10y and usdinr_rbi, 14 Oct), all others `backfilled`. `test_backfilled_rows_are_exactly_those_seen_after_their_first_nse_open` recomputes every label. My G5 (all `live`) and G6 (next calendar day instead of next session) are caught | MET |
| 3 | As-of rule at an explicit cutoff, with daylight saving, US holidays, same-day USD/INR at 15:00 but not 09:15, live view needs `first_seen_at` | `as_of.value_for` | My real probes (research / live views): **27 May 2025** (after US Memorial Day): sp500 and us10y give 23 May. **9 Mar 2026** (US switches to EDT on 8 Mar): 6 Mar; 6 Mar's close is available 02:30 IST, 9 Mar's 01:30 IST. **3 Nov 2025** (after the switch back): 31 Oct. **6 Jul 2026**: 2 Jul (3 Jul is the observed holiday). **14 Oct 2026, usdinr_rbi**: 13 Oct at 09:15, 14 Oct at 15:00 (13:30 IST rule); the live view gives none at 15:00 (first seen 15 Oct). Exact boundary: my G1 (`<=`) is caught. My G2 (local time read as IST), G10 (live view using the rule) and G3 (an unfinished close kept) are caught | MET (minor 1: no age limit) |
| 4 | Raw copies in Drive, never overwritten, logged; revisions and late values logged, never written into the table; append-only | `collector.py`, `table.merge` | One copy per fetch, filed by fetch time. The two Brent copies differ in bytes (453,367 vs 452,347) but give no revision row: the values are equal, and `verify` agrees. My G8 (fetch time taken before the downloads) and G9 (an adopted copy logged twice) are caught | MET |
| 5 | Gaps recorded; RBI and FBIL compared on shared dates; STALE named | `checks.py`, `job.py` | `check` output: "1086 dates compared, no difference"; `overlap_usdinr.csv` header only; gaps by kind as listed. STALE per source (7, 14 or 16 days) | MET |
| 6 | Failed download, bad file, empty answer or refused copy writes nothing and is named; Drive or setup failure is one line, exit 1 | collector, CLI | Read in the code: everything is downloaded and parsed before any save, and a save failure leaves the table alone. The builder's 42 mutations include these; I did not re-plant them | MET |
| 7 | Rows equal archived copies; `first_seen_at` not before the fetch; provenance recomputed; duplicates, order, empty named | `verify.py` | **Real `verify` against Drive, all six cues including the Drive-only ones: "every cue row equals the archived copy it names"** (29 s). **Independently:** I fetched the Treasury's 2026 daily par-yield CSV myself: **197 dates, 0 differences** from `us10y.csv`, latest 14 Oct 2026. My G7 (`first_seen_at` before the fetch accepted) is caught | MET |
| 8 | Interfaces, one composition root, no frozen file, gates | `GlobalCueSource`, `RowLog`, `wiring.py` | Concrete sources and stores only in `fno/global_cues/wiring.py`, listed in `CLAUDE.md`. No FREEZE-listed file changed | MET |
| 9 | Private cues: Drive only, write-once parts; repository holds copy logs only; fake test values; second same-day download refused; kept copies adopted at their fetch times | `row_log.DrivePartsRowLog`, `collector` `once_a_day`, `archived_copies` | Private search above. My G4 (a second download on the same day) is caught. The adopted copies' `first_seen_at` equal their path times (06:14:45 and 06:14:54 IST), after the copies were made | MET |

## Claims vs reality

| Claim | Reality |
|---|---|
| us10y 4,950 days, brent 4,992, usdinr_rbi 3,871, usdinr_fbil 1,981 | Matches the committed tables' row counts (each file has its line count plus a header) |
| "RBI and FBIL agree on all 1,086 dates they share" | True (`check`) |
| "sp500 4,977 days to 14 Oct 2026; nasdaq100 5,059 to 13 Oct 2026" | True (Drive, in memory) |
| "every cue row equals the archived copy it names" | True (my run) |
| Terms quotes for EIA, Cboe and Nasdaq | True, read by me today |
| "42 of 42 mutations caught" | Not re-run. **Mine: 10 of 10 caught** |
| "20 Jan 2026 gives Friday 16 Jan" after MLK Day | Consistent with my holiday probes (27 May 2025, 6 Jul 2026) |

## Findings

### Minor

1. **`value_for` has no age limit.** For 27 Nov 2026 it returns sp500's 14 Oct value in both views, six weeks old. On
   15 Oct, nasdaq100's "previous close" at 09:15 is 13 Oct, a day behind, because Nasdaq lacked 14 Oct; STALE is named
   only at run level. **No code calls `value_for` yet**, so nothing is affected today. Before M1, the weather or any
   forecast reads a cue:
   - `value_for` must refuse (or mark) a value older than its source's `max_age_days`;
   - the reader must check the returned `value_date` against the previous US session, or accept a lag stated in its
     own rules.
2. **FBIL in the public repository.** `usdinr_fbil.csv` is public. FBIL "does not authorize commercial use ... without
   written permission". This use is not commercial, but publishing a table in a public repository is redistribution.
   That is the owner's call (reasoning only); the builder already offers Drive-only.
3. **Muhurat sessions count as an "NSE open"** in the `live`/`backfilled` label (`calendar.next_session` includes
   them, but they have no 09:15 open). This errs toward `backfilled`, the safe side.
4. **`adopt` takes `first_seen_at` from the copy's path name.** It does not cross-check Drive's own creation time. This
   matters only for a hand-run command on the owner's private Drive.
5. **"At most one download a day" counts only saved copies.** A failed request may be retried the same day. This is
   documented. The owner's condition reads as one download a day; say so to the owner, or cap failed attempts too.

## The orchestrator's points

- **No private value anywhere:** MET; see the search above.
- **09:15 vs 15:00 cutoffs and `available_at`:** MET. The probes cover daylight saving both ways, US holidays, the
  13:30 IST reference rate at both cutoffs, and the exact boundary (G1).
- **`first_seen_at` never before the download:** MET. `verify` checks it on real data, G7 is caught, and the fetch time
  is taken after the last download (G8).
- **Once a day:** MET for saved downloads (G4); minor 5 for failed attempts.
- **Backfilled vs live labels:** MET (committed recompute test; G5 and G6).

## Project rules

- Lane 1 is right: new story, outside services, owner-restricted data.
- No secrets; no orders; no display code for the private cues.
- Owner decisions respected: Drive only, one download a day, no display.
- Quality rules: gap list, self-review, mutation proof and real outputs are present. The real outputs show dates and
  counts only for private cues.

## Verdict: PASS for 9b6515079cd55fea1d9fb97b4e9a022f1cb34ccc

All nine criteria are MET with my own evidence:
- no private value in the repository;
- Drive `verify` clean;
- the Treasury file equal to the table;
- the terms confirmed;
- 10 of 10 mutations caught.

Five minors. Minor 1 must be done before any consumer reads `value_for`; minor 2 is an owner item.
- **Merge:** as a merge commit, keeping both sides in the 5 conflicted files.
- **After the merge:** I check the recomputed merge, the branch files and CI.

## Addendum 1 (15 Oct 2026): merge check, A17 merged to main as 9a88b39

- **Parents.** 9a88b39's parents are c8ac9fd (main) and 9b65150 (the passed tip).
- **The merge matches my recomputation.** `git merge-tree --write-tree c8ac9fd 9b65150` conflicts in the 5 files I
  named. 9a88b39's tree differs from it only by the conflict markers, plus one blank line before "## A17" in
  `docs/stories/A-data-foundation.md`. Both sides are kept everywhere.
- **Branch files arrived unchanged.** Every file the branch changed is identical to 9b65150, except the 5 conflicted
  ones. Those gain only `main`'s own lines: the A15 and T1 roots, parser lines, rows and story section.
- **No unjudged change since.** From 9a88b39 to d67e9de only review, log, decision and manifest files changed.
- **CI.** Run 38672896611 (`checks`) on d67e9de, the first push carrying the merge: **completed, success**.
- **End-to-end run (rule 8).** The orchestrator records `global-cues verify` against Drive on the merged tree: "every
  cue row equals the archived copy it names". That matches my own run at 9b65150.
- **Minors.** 1 and 3-5 go to A17b, whose story text I check as judge 116. Minor 2 (FBIL public) is the orchestrator's
  logged decision, awaiting the owner.

**Merge check: PASS.**
