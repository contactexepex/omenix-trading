# Judge 79: P8 flows fixes, first day and filing by session (branches, before merge)

Date: 14 Oct 2026 (UTC). `story/p8-flows-by-session` at c59f862, which contains `story/p8-flows-first-day` a20e315.
Judged as one branch. Claims: `reviews/claude/response_78_p8-flows-first-day.md` and
`response_79_p8-flows-by-session.md`. Cause: judge 66 addendum 4 (the 13 Oct flows page published empty).

## Verdict: PASS (both). Three should-fixes; none blocks the 15:40 UTC deadline

## Gates (my runs, `python -B`, caches cleared)

- Full suite: 2,277 passed.
- Ruff, format (492 files) and imports: clean.
- `git merge-tree` with current `main`: clean.

## Real data (Drive read-only, the branch's own `FlowsReader`)

| Session | Cash days read | FII net | NSDL | Copies used | Problems |
|---|---|---|---|---|---|
| 13 Oct | 13 Oct | Rs −1,305.13 cr | 13 Oct | `fii-dii-cash` 13/ and `fpi-daily` 13/ | none |
| 14 Oct | 13 Oct only | Rs −1,305.13 cr | 13 Oct | the 14/ folders, both covering 13 Oct | "flows: no archived FII/DII cash copy covers the session 2026-10-14" |

So a re-publish of 13 Oct will carry its flows. A publish of 14 Oct without a by-session copy fails by name instead
of going out empty, which is what judge 66 asked.

## The claims to probe hardest

- **No look-ahead: met.**
  - A by-session folder D holds only a copy that covers D, because the folder is the session read from the copy.
  - The reader walks folders up to D only, so nothing from a later session is read for D.
  - My plant letting the reader look one day ahead is caught (5 failed).
  - The old run-dated folders 13/ and 14/ both cover 13 Oct. For 13 Oct, only 13/ is read.
- **A by-session copy can never be filed under a later session: met by construction.** The path is
  `path_for(session)`, where the session comes from the copy. A copy whose session is after the run's day is refused.
  My plants are caught:
  - filed under the run's day instead (1 failed);
  - the future-session check off (1 failed);
  - a later copy replacing the first (1 failed);
  - the old series winning over the by-session one (1 failed);
  - the reader's problems not stopping the build (1 failed);
  - a later by-session `first_day` (1 failed).
- **No double count:** a session in both series is taken from the by-session one (plant caught).
- **No existing Drive copy or manifest row touched:** the run-dated series stays in `RAW_SOURCES` for coverage and is
  no longer taken by any job.

## Should fix (not blocking)

1. **A refusal stops the rest of the archive step.** `_archive_session` runs the snapshot takes in one `try`. If the
   FII/DII copy is refused as covering a later session (a re-run of an old day after NSE has posted the next one),
   the NSDL take and the own corporate-action lists are skipped too. The publish still runs from what is archived,
   so no data is lost; the step just stops early.
   - Fix: skip that one take with a named note.
   - **Practical point today:** re-dispatch the 13 Oct publish before NSE posts 14 Oct's provisional values (usually
     the evening, IST). Then the archive step takes 13 Oct's copy into the new series without a refusal.
2. **A missing flows copy now stops the whole publication** (indices, chains, everything), not just the flows page.
   NSE's FII/DII API is a website endpoint that often blocks automated clients, so one outage would leave every
   dashboard page a day old.
   - This follows the orchestrator's "never an empty page" literally, but a flows-only failure (the flows page keeps
     the previous publication, the rest publishes, alert named) would protect the other pages.
   - Owner or design call (reasoning only).
3. **One plant passes:** dropping the reader's `covered <= day` check. In the by-session series it cannot matter (the
   folder is the session), so it is only a defence for the old run-dated folders. Add one test with an old-series
   folder holding a later session's copy.

**Information:** the by-session series keeps a session's **first** copy; the old series used the latest. If NSE ever
revises a provisional day after the first fetch, the revision is not kept. That is the price of point-in-time. State
it in the claims.

## Project rules

- New behaviour sits in a new class (`SessionFiledTaker`) behind the existing source and store interfaces, wired in
  `fno/storage/wiring.py`.
- A test holds every snapshot `first_day` to its committed manifest (it found the 5 P6 lists too).
- No secrets; alerts only to #fno-desk.

## Addendum 1 (merge check 2291088, and the re-publish of 13 Oct)

**Merge: MET.**
- 2291088 = 11b6cda + c59f862, equal to my recomputed merge.
- E2 merged at the same time (b4f1e1b). The merge joining the two lines, eb278c4, differs from a plain merge only in
  the hand-resolved `reviews/claude/README.md` index.
- CI `checks` is green on 2291088 (run 38509482330) and on 6f8c859 (run 38510047526), which holds both.

**The re-publish of 13 Oct (run 38509504961, from 2291088): MET.**
- The archive step seeded `nse/flows/fii-dii-cash-by-session` and `nsdl/fpi/fpi-daily-by-session` for 13 Oct. Its
  manifest row's SHA-256 `216a4b93…` equals the run-dated 13/ copy's, so the values are the same.
- The publish (`nse-2026-10-13-c3b50f940a73`) read back all 1,110 pages equal.
- The flows page hash changed from the empty page's `7e3bf91b…` to `a34b1991…`.
- The log shows both by-session copies read, and "publication inputs: 2 row(s) added". The rows are committed in
  2fdf096.
- I recomputed the cash row's `copies_sha256` (`c253e74f…`) from its line `2026-10-13 2026-10-13 216a4b93…`:
  equal.
- I re-ran `FlowsReader` on `main` (Drive read-only) for 13 Oct: FII net Rs −1,305.13 cr, DII +2,439.24 cr,
  NSDL FPI +2,000.73 cr, from the two by-session copies. That is what the page was built from. I did not read the
  Azure row itself; I never connect to Azure.

Judge 66 item 4 is now met as well (see judge 66 addendum 5).

## Addendum 2 (hardening branch 19b8162, the three should-fixes): PASS

1. **`covered <= day` is tested.** A new test has an old run-dated folder holding a later session's copy. My plant
   dropping the check is now caught (1 failed).
2. **"First copy kept" is stated** in `SessionFiledTaker`'s docstring and the story: a later NSE revision of a
   provisional day is not kept, and that is the price of point in time.
3. **A refusal no longer aborts the archive step.** A copy covering a later session raises `LaterSession`, a
   `ValueError` subclass. `_take_snapshots` catches only that, prints the named note, and still takes NSDL and our
   own lists. A failed content check still stops the step. My plants:
   - the refusal not caught: caught (1 failed);
   - every `ValueError` swallowed (a damaged file passing silently): caught (1 failed);
   - the refusal raised as a plain `ValueError`: caught (1 failed).

**The builder's correction is right.** I read `MarketRun._publish`: the archive step's problem stops the
publication as `archive_incomplete`. So before this fix, a refusal stopped the whole publication, not only the rest
of the archive step. My note in this file understated it.

**Gates (`python -B`, caches cleared):**
- branch: 2,281 passed; ruff and imports clean;
- `git merge-tree` with `main` conflicts only in the `reviews/claude/README.md` index. The code areas do not overlap
  with E2, D6 or E6.

**Condition:** run the full suite on the merged tree before pushing to `main`, as always.

**Verdict: PASS.** The whole-publication rule for a missing flows copy is unchanged and waits for the owner.

## Addendum 3 (merge check, 72a40b6)

**MET.** 72a40b6 has parents 7d08b53 (main) and 19b8162 (the passed tip). It differs from a plain merge only in the
`reviews/claude/README.md` index. No other code reached `main` since. CI `checks` is green on 72a40b6
(run 38513093242).
