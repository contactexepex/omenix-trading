# Judge 197: E4c code, the entry check before any fill: `story/e4c-protective-leg-refusal` f4a1f642 (lane 1)

Judge B. The E2c/C5 builder. Story `docs/stories/E-paper-desk.md` E4c (text PASS, judge 120 addendum 1). Claims:
`reviews/claude/response_184_e4c-entry-check.md`, renamed from 177; the rename commit changes no code. Rebased on
`main` ac3d6abf. It touches fills, so rule 9 applies: ChatGPT reviews after this PASS.

## Gates (exact SHA, FNO_SLACK_BOT_TOKEN unset)
- **6,357 passed, 0 failed.** Ruff and imports are clean.
- `fno/constants.py` is 335 lines and `entries.py` 170, under the limit.
- `tests/desk` + `tests/timetable`: 199 passed.

## Criteria
| # | Result | Evidence |
|---|---|---|
| 1 Check before any fill; failure is `not_opened` with one code; no fill, no ledger row | MET | `entry_problems` runs in `EntryDesk.enter` after C3 and `refusal`, before `FillMaker` and any `record_fill`. On a problem: one `not_opened` event with `problems[0]`. Tests assert no fill rows and an unchanged account |
| 2 Boundaries 64/65/66 for a protective bid, a protective ask and a short bid; multi-leg; one-leg | MET | `test_entry_check.py` (26 tests), including STR1's LC, LP, CCS and PCS |
| 3 Not buyable (no quote; A4-invalid; ask size short) and short not sellable, with no unwind | MET | A4-invalid cases and a second protective leg missing give `protection_not_buyable` with nothing bought. A short A4-invalid leg gives `short_leg_not_sellable`. `legging_cost_rs is None` in both |
| 4 Order C3 → refusals → check → limit → fills; first failure recorded; rerun replays | MET | Code order as listed; a test checks the entry check runs before the limit. A replay returns `_result(done[0])` before the check, so `refused_by_check` stays False on a replay. **My plant:** reversing the problem order fails 1 test |
| 5 No quote figure in the reason or event | MET | `PROBLEM = "{code} ({contract}, {units} units)"`. A test reads every column of the event row against the snapshot's figures |
| 6 Exception 3 gone; E2b text lists two | MET | E2b's pinned test now expects `not_opened` and no row at all. E2b criterion 3's text names the two exceptions and says the third was removed by E4c |
| 7 One alert ending "information, no action"; without a token it prints and the run goes on | MET | `daily_steps` alerts only when `refused_by_check`, prints the outcome when it is not `SENT`, and sends no alert on a replay or an entry-limit refusal (4 tests). **My plant:** alerting on any `not_opened` fails 2 tests |
| 8 Guard: the unwind still runs after a failure that passes the check | MET | The `check_passed` double makes `entry_problems` return `[]`. The moved unwind tests keep their assertions unchanged (I read the diff: no assertion dropped). The unwind code is unchanged |
| 9-13 Later snapshots unchanged; C5; E8 hook; never an order call; standards | MET | The exits code is untouched. A C5 `session_trades` test exists. `entry_problems(snapshot, legs, units)` depends only on its snapshot, so E8 can call it. No order call. Small new module, constants in `constants.py` |

**My other plants:** dropping the protective closing-side check fails 14 tests; giving every opening failure the
protective code fails 4. The builder reports 12 plants, all caught.

## The builder's points
- **(a)** Keeping `all(q.fills ...)` before the entry limit is right. In the guard path a leg can fail, and
  `maker.fill` must not run on it.
- **(b)** Printing the outcome for this alert only matches criterion 7.
- **(c)** Agreed. Since E2c the desk records are in Drive, so the privacy half no longer applies. The value is money:
  no spread paid twice (path 1 and the unwind), and no part of C5's daily new-risk budget used.

## Note (not blocking)
E2b's gap-table row (`E-paper-desk.md` line 372, "E4 criterion 2 ... kept; the one stated exception") still reads as
before. Since E4c, criterion 2 is reachable only through the guard. Align the row at the next edit.

**Verdict: PASS for f4a1f642.** ChatGPT's review follows (rule 9). Any change from it comes back to me before the
merge.

## Addendum 1 (15 Oct 2026): b1de45e9, after ChatGPT review 123 (ACCEPT, no code change)

- **f4a1f642..b1de45e9 changes no E4c code.**
  - Every file E4c changed has the same E4c diff against its base as at f4a1f642. Checked file by file: the only
    byte changes in `fno/constants.py` and `tests/desk/test_entries.py` come from the `main` merge, bb1b06f4.
  - The rest is the E2b gap-table row, which closes my note; ChatGPT's review 123 and its index line; response 186
    and the log; and d5ec6c43, two Known-limits lines.
- **The two lines are accurate.** Shared displayed size across same-book entries on one contract predates E4c.
  `book1_orders` returns every traded opportunity, so the path can open once two approved strategies share a contract,
  and the stated fix (sum the book's units per contract before any fill) is right. The second line: one immutable
  snapshot cannot model the book changing between legs.
- **Suite on b1de45e9** with `-n auto`: **6,556 passed, 0 failed**.

**PASS for b1de45e9.** Merge it.
