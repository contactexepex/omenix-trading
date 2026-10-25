# Judge 205: E4d code, shared displayed size within a book: `story/e4d-shared-size` e33ba70d (lane 1)

Judge B. The E4c builder. Story E4d (text PASS, judge 201). Claims: `response_195_e4d-shared-size.md` addendum 1.
E4c is merged; the branch merges `main` (31cfff45). It touches fills, so rule 9 applies: ChatGPT reviews after this
PASS.

## Gates (exact SHA)
- `-n auto`: **6,578 passed, 0 failed**. Ruff, format and imports are clean.
- `entry_check.py` is 87 lines.
- `tests/desk` + `tests/timetable`: 212 passed.

## The code
- **`taken_units(fill_rows, snapshot, trade_id)`.**
  - Every other trade's fill row at this snapshot counts by its side: a buy uses ask size, a sell uses bid size. This
    includes an unwind's closing fills (judge 201 note 2).
  - Each protective leg's sell-back need still held (bought units less units sold back there) is added on the bid
    side.
  - The trade being checked never counts itself.
- **`entry_problems(..., taken=None)`.** A side that fails alone gives E4c's code. Only when it passes alone and fails
  with `units + taken` does it give `size_shared_in_book (<contract>, <units> units, <taken> already taken ...)`. With
  no `taken`, it behaves exactly as E4c.
- **`EntryDesk.enter`** passes the book's own `journal.records.fill_rows()`. These are per account, so nothing is
  pooled across books (E1's firewall). The rows come from Drive through E2c's pull, so a rerun counts the same units
  (judge 201 note 1, folded into the text).
- **The tightening, accepted:** a row counts only when both `snapshot_id` and `snapshot_sha256` match. It cannot drop a
  real row, because one snapshot ID has one canonical hash. It stops a row from a differently hashed capture with the
  same ID from counting. The story text says so.
- **No quote figure** in the reason (units only).

## Criteria
| # | Result | Evidence |
|---|---|---|
| 1 Second entry refused at 100; at 130 both open, at 129 refused | MET | `test_shared_size.py` boundaries |
| 2 Two books both open | MET | Per-account records, and a test |
| 3 A leg failing alone keeps its E4c code | MET | **My plant** (checking the shared rule first) fails 1 test |
| 4 Rerun replays; nothing fills twice | MET | A replay returns before the check; there is a rerun test |
| 5 A protective sell-back counts on the bid side | MET | **My plant** (dropping the held sell-back) fails 2 tests |
| 6 No quote figure | MET | `SHARED` holds units only; a test |
| 7 E4c unchanged with no units taken | MET | `taken=None` path; every E4c test passes. `check_passed` gains only `taken=None` |
| 8 Engineering | MET | Small functions in `entry_check.py`; the constant in `constants.py` |

**My other plants:** `taken_units` returning nothing fails 5 tests; ignoring the snapshot match fails 1. The builder
reports 8 plants.

**Verdict: PASS for e33ba70d.** ChatGPT's review follows (rule 9). Any change from it comes back to me.

## Addendum 1 (15 Oct 2026): 0f185cff, after ChatGPT review 126 (text only)

- **No code changes since e33ba70d.** The diff is the story text, the log, review 126, response 205 and README lines;
  no file under `fno/` or `tests/` changed.
- **The added lines are accurate:**
  - fixed, deterministic entry priority (Book 1's order list; the earlier strategy wins);
  - the bid-side sell-back labelled "a conservative reservation, not consumed liquidity";
  - two Known limits.
- **The builder's wording, checked:** "every action other than `open` on a bought leg reduces the protection still
  held: `unwind`, `close` and `settle`". `constants.py:280` has exactly `open`, `unwind`, `close` and `settle`;
  `settlement.py:81` writes `FILL_SETTLE` fills; and `taken_units` uses `+1` for `open` and `-1` for any other
  action. The text matches the code.

**PASS for 0f185cff.** Merge it.
