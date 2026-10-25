# Judge 72: story E2, the common market pack and book-private packs (branch, before merge)

Date: 14 Oct 2026 (UTC). Branch `story/e2-market-pack` at 87202e4 (a883a77 merged with main 51aa2e7). Claims:
`reviews/claude/response_74_e2-market-pack.md`. Story: `docs/stories/E-paper-desk.md` E2.

## Verdict: FAIL, three must-fixes (two are missing tests, one is a small design fix); the code I read is otherwise sound

The core works:
- the real rebuild is byte-identical;
- the common pack holds no book data;
- the private packs are kept apart.

But 9 of my 14 plants pass the 26 tests unseen. Two of them sit on the questions the orchestrator asked: the
opportunity set's approval filter (criterion 5) and "without a time is refused" (point a). The CLI can also freeze an
empty pack for the day, with no way back.

## Gates (my runs on 87202e4)

- Full suite: 2,304 passed.
- `ruff check`: clean. `ruff format --check`: 504 files already formatted.
- `tools/check_imports.py`: clean.
- `tests/packs`: 26 passed. All new files are under 350 lines (the largest test file is 139 lines).

## The judge's own check from the story

**Rebuild from committed inputs: MET.** In a clean worktree I ran `python -m fno desk pack --day 2026-10-13`, deleted
both packs, and ran it again. Both files were byte-identical:
- common pack: `b62467e6…`;
- Book 1's private pack: `488b1294…`.

`sha256sum -c common.sha256` says OK.

**Grep the common pack for book fields: MET.** `book1`, `book2`, `book3`, `journal/`, `positions` and `cash_ledger`
give 0 hits.

**Real repository result.** The pack has 262 items:
- the session;
- 260 closes;
- one event.

`a4_snapshot.snapshot_id` is null and the opportunity set is `no_trade` only. With the golden snapshot copied into
`research/data/quotes/`, the same command gives 282 items, VIX at 14:59 with its NSE source, and 0 refused.

## Per criterion

| # | Criterion | Check | Result |
|---|---|---|---|
| 1 | Common pack holds no `journal/<book>/` field | Inputs read only market files. Planted-position test passes, my grep is clean, and the leak guard refuses a pack naming a book. Plant P10 (guard reduced to book names, `journal/` dropped) is **not caught** | MET (minor test gap) |
| 2 | A private pack never holds another book's data, each pair | 6 ordered pairs tested. My plant P5 (resolve check against the repository root, not the book's folder) is **caught**. Builder's link, `..`, packs and dot-file plants are caught too | MET |
| 3 | Twice from the same inputs: byte-identical | Tests plus my real rebuild above | MET |
| 4 | An input after the cutoff refused with its name | The 15:00:01 test passes, but see the point-in-time plants below: response time, untimed VIX and the exact boundary are untested | **PARTLY** |
| 5 | Opportunity set equals a hand computation | The hand computation (23 Nov expiry entering a 30-41 day window on 13 Oct; a 30-45 window opened earlier) is right: I checked the day counts. But the fixture has only approved versions. Plant P14 (any registered version offered, status ignored) and plant P6 (the first registry row wins, so a version approved and then paused is still offered) both pass all 26 tests | **PARTLY** |

## My plants (14; each restored; `tests/packs` run each time)

| Plant | Result |
|---|---|
| P5 resolve check against the repository root | caught (1 failed) |
| P8 session item untimed | caught (3 failed) |
| P11 store overwrites a different pack | caught (1 failed) |
| P12 refused list dropped from the pack | caught (3 failed) |
| P14 approval status ignored (research and paused versions offered) | **not caught** |
| P6 earliest registry row wins (approved, then paused, still offered) | **not caught** |
| P3 option row timed at `request_sent_at` instead of `response_received_at` | **not caught** |
| P4 VIX without NSE's timestamp admitted at the first request time | **not caught** |
| P1 an item at exactly 15:00:00 refused (`>=`) | **not caught** |
| P2 duplicate item names allowed | not caught |
| P7 past events (dated before the day) kept | not caught |
| P9 only 20 closes kept instead of 260 | not caught |
| P10 leak guard without `journal/` | not caught |
| P13 the snapshot CSV hash dropped from provenance | not caught |

The builder's 11 mutations are real, but they cover the paths it thought of. The code is correct in all 14 places today
(I read each one). What is missing is the test that would notice a later change.

## Must-fix

1. **Opportunity set status (criterion 5).** Add fixture versions with status `research`, with `paused` after
   approval, and with an approval dated on the day. Expect only the approved-before-the-day version plus `no_trade`.
   P6 and P14 must then fail. A paused strategy wrongly offered to every book's scoreboard is exactly the error
   scoreboard A must never make.
2. **Point-in-time tests (criterion 4, orchestrator's point a).** Three cases:
   - a quote sent at 14:59:59 and received at 15:00:01 is refused (P3);
   - VIX with no or unreadable NSE time is refused as untimed (P4);
   - an item at exactly 15:00:00 is kept (P1).
3. **Do not freeze an empty pack.** On a session day with no canonical A4 snapshot, `desk pack` writes a pack with no
   quotes, prints "refused items: 0" and exits 0. The store is write-once, so when the recorder commits at about
   15:13, that day's pack can never be rebuilt with the snapshot. Every book would then decide on nothing.
   - **Fix (reasoning only):** on a session day, refuse with a named reason (`no canonical A4 snapshot for <day>`) and
     a nonzero exit, writing nothing.
   - A closed day may still write its session-only pack.
   - One test.

## Should fix (one test each, small)

P2, P7, P9, P10 and P13 above. P13 matters for the story's "rebuild from committed inputs": the provenance is what
names the input files.

## Orchestrator's questions

**(a) Source and time, refusal after 15:00 or untimed.** Every item carries `source` and `available_at`, and
`admit` refuses untimed and late items, listing each by name (code read). Two caveats:
- the refusals the orchestrator asked about are untested (must-fix 2);
- events with no `announced_on` are dropped before admission instead of listed as refused. The real events file has
  3 such rows, none dated 13 Oct or later, so this is information only.

**(b) Book isolation.**
- All 6 ordered pairs are tested.
- A link or `..` resolving outside the book's folder is refused; my subtler plant P5 is caught.
- Information: Book 1's pack takes all of `playbook/`. D4 puts Book 2's envelope files there
  (`playbook/<name>-v<n>.envelope.yaml`), so Book 1's pack will hold Book 2's envelope. An envelope is a frozen rule
  file, not positions, decisions or memory, so I accept it under the story's definition. D4 should state it.

**(c) Rebuild-stable bytes.** MET (tests plus my real rebuild).

**(d) "An approval counts from the next session", and D2's merged code.**
- **Not consistent today.** D2 (`fno/playbook/evaluate.py` line 48) uses `playbook.approved()`: the file's current
  status, with no date.
- A version approved during a session is evaluated by Book 1 that day but is missing from the common set.
- A version paused during a session is dropped by Book 1 at once but stays in the common set (E2 counts the change
  only from the next session).
- No version is approved yet (`playbook/registry.csv`), so nothing is wrong live today.

**My recommendation (risk manager, reasoning only):**
- D2 should take approvals as of the start of the day, as E2 does.
- D2 should take pauses and retirements at once, never from the next session. The hard-loss pause (E6) must stop new
  risk the moment it fires.
- The common set may keep a version paused today: it was a real opportunity, and Book 1's outcome for it is
  "no trade (paused)".
- So D2's filter becomes "approved before today AND still `paper` now". Please give D2's change that rule, not a
  plain "as of the start of the day".

**(e) "No A4 snapshot committed on main yet".**
- **The claim is true.** `research/data/quotes/` does not exist on `main`. No commit has ever touched it, and the only
  quote snapshots in the repository are G1 v2's golden fixtures (provider `golden-fixture`, made-up prices).
- `quote-recorder-nse.yml` has **0 runs**. It landed at 21:42 IST on 13 Oct, so its first run is today at 14:20 IST.
- I cannot see the Groww routine's 13 Oct session. It committed nothing, although 13 Oct was a trading day.
  **Please check that routine's 13 Oct result and its 14 Oct run**; a recorder that silently records nothing is a
  separate problem from E2.
- E2's tests should keep the golden fixture: it is committed and stable, while a real day's file arrives later. Once
  a real snapshot is committed, one wiring test on it (items admitted, times from the real rows) would add a real-data
  check.

## Claims vs reality

| Claim | Reality |
|---|---|
| "2304 tests pass" | Confirmed (my run) |
| "11 of 11 mutations caught" | Plausible; I did not re-run theirs. My 14 plants found 9 gaps (above) |
| "Rebuilding from committed inputs gives the same bytes even after later downloads" | Confirmed on the real repository for 13 Oct |
| "The common pack holds market data only" | Confirmed by grep and by code read |
| "No A4 snapshot is committed on `main` yet" | True (question e) |
| "Committing is left to the daily run" | True. With write-once, the run order then matters: must-fix 3 |

## Project rules

- New composition root `fno/desk/pack_wiring.py`, listed in CLAUDE.md.
- Inputs sit behind `CommonInput`. D2's `OpportunityFinder` is reused (DRY), and the frozen G1 closes code is imported,
  not changed.
- Constants are in `fno/constants.py`. No orders, secrets or Slack.
- Branch rule followed: nothing on `main` before this verdict.

## Addendum 1 (where the 3 pm snapshots live; plants re-run without bytecode caching)

**Snapshots live in git, not Drive.** The orchestrator reported that the A4 snapshots go to Drive. The code says
otherwise:
- `build_quote_store()` is `LocalFolderStore(research/data/quotes)` ("repository: Drive is read-only here",
  `fno/storage/wiring.py`).
- The recorder, E4's execution snapshots, E2's pack and the forecast's live capture (`baseline_wiring.py`) all read
  that folder.
- `quote-recorder-nse.yml` commits `research/data/quotes/nse`.
- CLAUDE.md's routine step 3 commits `research/data/quotes/`.

So `git log --all -- research/data/quotes` being empty means no 3 pm snapshot was ever recorded and committed, 13 Oct
included. It does not mean they are elsewhere. Today's 14:20 IST NSE run and the Groww routine are the first real test.
If either writes to Drive only, every reader above finds nothing.

**Plants re-run with `python -B` and every `__pycache__` removed first:** all 14 gave the same results. The verdict
stands.

## Addendum 2 (round 2, branch be9bc5e): PASS

**All three must-fixes are met, and so are the five should-fixes.** I re-ran my 14 plants (`python -B`, every
`__pycache__` removed first): **all 14 are now caught.** They include:
- the approval-status filter (P14, P6);
- the response time (P3), the untimed VIX (P4) and the exact 15:00:00 boundary (P1);
- the leak guard's `journal/` (P10) and the provenance hash (P13).

**Empty pack: met.** On the real repository, `desk pack --day 2026-10-13` now prints "refused: no canonical A4
snapshot for 2026-10-13 (regular session): nothing written", exits 2 and writes no file. A closed day (11 Oct, a
Sunday) still writes its session-only pack.
- **Run order:** this fixes the order: pack only after the 3 pm snapshot is committed. E3 must schedule it that way.
- **A retry capture after 15:00:** if the canonical snapshot is such a capture, every quote is refused as after the
  cutoff. The pack is then written with no quotes. That is the honest point-in-time state, not a defect.

**Gates:**
- branch: 2,316 passed; ruff, format and imports clean;
- my trial merge with `main` (which now has D2 start-of-day): 2,324 passed. `tests/packs` and `tests/playbook`: 286.

**Note for the follow-up:**
- `tests/packs/builders.py` still builds `Playbook(strategies, frozenset(keys))`. Since D2 merged, `Playbook`'s second
  field is the registry rows. E2 never reads it, so nothing fails, but it is the wrong type.
- When E2 switches to `Playbook.approved_on`/`status_on` (one rule, as agreed), pass the rows.
- E2's common set keeps a version stopped on the day; Book 1 drops it at once. That is accepted (judge 74).

**Verdict: PASS.** After the merge I check `main` against be9bc5e and CI. The `desk` parser must be folded into E6's
one `desk` parser by whichever of E2 and E6 merges second (judge 73), with the full suite on the merged tree.

## Addendum 3 (the delta be9bc5e..b2749a6): PASS

**The change:**
- E2's own `approved_on` copy is gone. The opportunity set now reads `Playbook.status_on(day)` (D2's start-of-day
  rule; one rule, DRY), and the builder passes the loaded `Playbook`.
- `LoadedPlaybook` and `registry_rows` are gone.
- `tests/packs/builders.py` now builds `Playbook(strategies, rows)`, so my frozenset note is closed.
- A version stopped on the day stays in the common set. Book 1's own gate (`approved_on`) drops it, as accepted in
  judges 72 and 74.

The rest of the diff is `main` merged in (D2, A12), which is already judged.

**Checks (my runs, `python -B`, caches cleared):**
- my 14 plants, adapted to the new code: all 14 caught. That includes reading the playbook "through the day" instead
  of at its start (2 failed) and ignoring the status (1 failed);
- full suite: 2,324 passed;
- ruff, format and imports: clean;
- `git merge-tree` with current `main`: clean;
- 13 Oct on the real repository is still refused, with exit 2 and nothing written.

**Verdict: PASS for b2749a6.** After the merge I check `main` against b2749a6 and CI. The `desk` parser fold with E6
remains for whichever branch merges second.

## Addendum 4 (merge check, b4f1e1b)

**MET.** b4f1e1b = 11b6cda + b2749a6, equal to my recomputed merge. `main` now equals the passed tips of E2, P8 and
D6 merged, plus resolutions of the `reviews/claude/README.md` and `fno/cli.py` conflicts:
- the `fno/cli.py` resolution keeps both `add_desk_parser` (E2's `pack`) and D6's `add_versions_parser`;
- `fno desk pack` and `fno versions` both work on `main`.

My full suite on `main` 0f4e888: 2,368 passed. CI `checks` is green on 6f8c859 and 0f4e888 (run 38510606597).

**For E6:** `main` has E2's `desk` parser (`fno/desk/pack_cli.py`). E6's merge must fold `pack` into its single
`fno/desk/cli.py` parser; I check that merge commit.
