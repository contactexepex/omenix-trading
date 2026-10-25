# Judge 248: P2c part 1, the paper books page's accounts (`paper_trades`) and the 2.11.0 pin

Trading `story/p2c-paper-books` at 69503b1c (P2 builder 013xqaNTCbSBytKgqpfaYFqZ; claims: response 239). Story W3
Part 1, build step 3. Lane 1. Judge D, 16 Oct 2026.

**FAIL: one should-fix**, the same root cause as judge 244 (P2b).

| Item | Result | Evidence |
|---|---|---|
| The 2.11.0 pin | MET | All pinned `api/` files are byte-identical to `git archive e425aea api` (`diff -rq` lists only the unpinned README, catalog and paths). `git diff e425aea <dashboard main> -- api` is empty. |
| One account per book, never added | MET | `paper_trades` writes three accounts in `BOOK_FAMILIES` order (strict zip), with no total. The marks come from the last `equity_history` row on or before the session (as Home's books, P10). `opening_value` is the capital in force that day (E1b). A book not opened shows its opening balance. |
| Limits from C5, never typed | MET | `open_risk_cap` = `profile.open_risk_cap_rs` and `pause_at` = `profile.drawdown_brake_rs`, both read through `ProfileSettings` (judge 224 addendum 3's note met). |
| Brake = C2's own figures | MET | `closed_equity_series`, `high_water_mark` with `brake_restarts` and `equity_at`. A history C2 refuses stops, named. It is 0 today. |
| Privacy | MET (tests) | Accounts arrive only through E2c's download. A planted Drive-only value reaches the payload and no file (tree compared); the stop names no amount. |
| Gates | MET | On 69503b1c: 6958 passed (`-n auto`, Slack token unset), ruff check and format clean, check_imports clean. A trial merge with main conflicts only in reviews/claude/README.md (both rows kept); then 7081 passed. |

## Finding (should-fix)

**Any shadow account, or any paper trade, stops the whole market publication.** `PaperBooksReader.on` raises
`FiguresNotComputed` for a shadow account (any folder under `journal/shadow/`) or a trade, and `market_run.py:117`
stops every page on it. The claims state this plainly and point out that Home's open-trade stop already carries the
same risk. But part 1 adds two new triggers that normal running will meet soon:
- **Shadow accounts:** R3 part A (account opening) is merged and part B is in progress; B0 is the registered
  measurement account. The first daily run that opens a shadow account under `journal/shadow/` stops every dashboard
  page until P2c part 2 lands.
- **A closed trade:** a book's first closed trade stops it too (Home stops only on an open trade).

As with P2b, a page that does not build a case yet must hold only itself. **The root cause is that a page cannot
fail alone.** The owner's per-page hold (16 Oct, "its own story, next") is the fix for P2b, P2c and Home's existing
open-trade stop alike: one design, not three patches.

**Fix:** land the per-page hold first, and have `paper_trades` (and P2b's `forecast_lab`) hold only their own page,
with the named alert, while every other page publishes. Rebase P2b and P2c on it. Add a test where a planted shadow
account and a planted closed trade leave every other page published.

## Notes

- P2c part 2 (the trade mappings) waits for the screens lead's answers to the ten questions; that is fine once a
  missing mapping holds only this page.

## Addendum 1: head dd0d34d1 (rebased on P11 and P2b; part 2 built)

**FAIL: one should-fix.** Judge 248's finding is fixed at its root.

**Met:**
- **The page holds only itself:** the reader and the closed-trades module raise the page's own
  `PageCannotBeBuilt(reason)`, and the block raises `PageHeld`, so only `paper_trades` is held (shows previous_page)
  and every other page publishes. A full `MarketRun` test shows this, with `page_holds` and exactly one alert line.
- **Normal running is now built, not held:** a shadow account gets its own card, and a closed trade gets C1's
  `trade_line` money (gross, the pads and charges as costs, net). The strategy is "Strategy <k>, version <n>", with k
  the order of first appearance in the append-only registry, so the version tag is never sent. The structure is in
  plain words. The exit is the desk's rule name mapped, or `expiry_settlement`, or `other`.
- **Still held:** an open trade (no per-trade marks yet), a strategy with no registry row, an unknown structure, and a
  brake history C2 refuses.
- **The reasons:** every one is tested against the pinned pattern. The open-trade sentence is 2.13's example word for
  word.
- **Gates on dd0d34d1:** 7226 passed (`-n auto`, Slack token unset), and `market contract-check` gives 2.13.0 "same as
  the dashboard's". A trial merge with main conflicts only in reviews/claude/README.md (the known artifact).

## Should-fix: B0 would be shown as a candidate, not as the measurement account

`_shadow` gives every shadow account the label `SHADOW` ("B0 is measurement once R-factory marks it; none is yet").
But B0 is already marked:
- `playbook/b0-monthly-sc-v1.yaml` has `edge_family: measurement`, on main with its registry row;
- `fno/playbook/measurement.py` is the one source for that label ("every output that shows such a version" must say
  so).

The contract defines `shadows[].label` as "shadow = a candidate tested on paper beside the books; measurement = B0".
B0's account opens from about 19 Oct (the orchestrator, R3). From then on the paper books page would show B0 as a
candidate strategy, the opposite of the owner's decision 1 A ("a MEASUREMENT shadow … Never promoted").

**Fix:** label each shadow through `fno/playbook/measurement.py` (`edge_family == measurement` gives `measurement`, and
anything else `shadow`), not a constant. Add a test with B0's real version file giving `measurement`, and a candidate
giving `shadow`.

## Addendum 2: head 0ae25471 (B0's label)

**PASS: P2c may merge once main is green, after P2b.**
- **The label:** each shadow's label now comes from R3's one source. `PlaybookVersions` reads D1's playbook loader,
  and `is_measurement(found)` gives `measurement`, anything else `shadow`. A version file that cannot be read holds the
  page with a fixed, digit-free sentence (tested against the pattern with the other reasons).
- **The test:** B0's real playbook file and real registry give ("Strategy 1, version 1", "measurement"), a candidate
  gives "shadow", and an unreadable file holds the page. **My mutation** forcing every shadow to `shadow` fails it.
- **Gates on 0ae25471:** 7370 passed and 3 failed, the same 3 risk tests red on main (judge 178 addendum 17). ruff and
  check_imports clean.
- **Note:** `PlaybookVersions` loads the whole playbook, so one broken playbook file holds the paper books page for
  every shadow. That is a loud, page-only hold, so it is acceptable.
