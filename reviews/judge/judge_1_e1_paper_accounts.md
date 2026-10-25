# Judge 1: story E1, paper accounts per book with a single-writer lock

Verdict: **PASS** (no blocking, no should-fix findings; 5 minor findings below, for the builder or the later stories
named).

Judged on `main` at 8ad2885 (E1 commit 72fbb47, available-cash change 655dcaa). Read in full: `fno/books/*.py`,
`fno/composition.py` (account part), `tests/books/*`, `journal/*/account/*`, story E1, response 37, C2's
definitions, `docs/DESK_DECISIONS.md`.

## Checks run by the judge

```
$ python -m pytest -q                 238 passed
$ ruff check fno tests tools          All checks passed!
$ python tools/check_imports.py       clean: 89 files, 1 archival skipped
$ git log -- journal/book1_rules/account   one commit (72fbb47): starting state committed once
```

Own two-writer run (story's "judge verifies"), separate script, real processes released at the same instant, each
holding the lock 1 s:

```
--- same book x2
B: busy "book1_rules: another writer holds the account (...)"  exit 3
A: applied true                                                exit 0
--- different books
C (book1_rules): applied true exit 0   D (book2_hybrid): applied true exit 0
ledger book1_rules: opening, A, C      ledger book2_hybrid: opening, D
```

## Criteria

| # | Criterion | Builder's claim | Judge's own evidence | Result |
|---|---|---|---|---|
| 1 | Rs 5,00,000, no positions, committed once | `account.py:137`, committed files | Read all nine committed files: opening row 500000.0, no fills, equity row 500000/500000/0 trades; one commit touches them; `start` returns False if the ledger exists (`account.py:140`); test reads the repository's own files | MET |
| 2 | Same book, two processes: one writes, the other exits without writing | `lock.py` LOCK_NB -> `AccountBusy`, CLI exit 3 | My run above: exit codes 0 and 3, one fill; builder's process test also passes | MET |
| 3 | Two books at once both succeed | separate lock per book | My run above: both exit 0, each ledger has only its own fill | MET |
| 4 | Crashed holder freed only after lease expiry and holder gone; never while alive | `lock.py:151-168`, `holder_alive` with `/proc` start time | Read `_check_previous_lease` (`lock.py:151`): live holder -> busy; dead holder + unexpired lease -> busy; both -> taken over. Three process tests (SIGKILL holder; live holder with expired lease; lease naming a live PID without flock) pass and test what they claim | MET |
| 5 | Restart after interrupted write neither loses nor repeats a fill | fill-ID idempotency, half-line recovery, fsync before view | Read `apply_fill` (`account.py:149`), `_recover` (`:185`), `_complete_lines`; the two crash tests SIGKILL the writer after a full line and half-way through a line, then retry: f-1, f-2, f-3 exactly once, view rebuilt. A reused ID with other content raises (safe direction) | MET |
| 6 | No code path reaches another book's files | `paths.py`, writer checks lock book and folder | Read `paths.py`: unknown book, separators, `..`, file links and folder links refused; tests cover file link, folder link, `../` names, another book's lock, same-name book in another root | MET |

## Claims vs reality

- "Definitions implemented in `fno/books/equity.py:78-110`; available cash at `:75`": true (lines 74-78 and 81-112 in
  the current file); `marked equity = cash + marked open value` holds by construction (`closed + open cash flow +
  open value`) and is tested.
- "A missing mark raises `MissingMark`": true (`equity.py:97`), tested. No price is invented; a sell fill price is
  floored at 0 by C1's `Order.fill_price`.
- "Two processes start at the same instant ... exit codes [0, 3]": true, reproduced independently.
- "191 passed": historical; now 238 with later stories, all passing.
- "Largest file 211 lines": true (account.py 211, lock.py 180).
- Doubts 1-7: all accurate. Doubt 1 (lock is one machine only) is correct and important; see finding 2.

## The available-cash change (13 Oct): judged right

`available cash = min(cash, marked equity) - margin blocked - premium reserved`.

- Long option (strong evidence, arithmetic, test `test_available_cash_never_counts_a_bought_premium_as_spendable`):
  buying at 100.5 x 65 lowers cash by 6,532.50 + charges while marked equity barely moves; the old "marked equity -
  margin" let that premium be spent again. `min` picks cash. Correct, and it matches how a broker treats a bought
  option (its value is not spendable).
- Short option (some evidence): `min` picks marked equity, so neither the premium received nor an open loss is
  spendable. Safe. It can be stricter than a broker: if C2's margin figure is the broker's total (SPAN + exposure,
  which already reflects the short option's current value), the short's value is counted twice. That can only
  block a trade, never enlarge one, so it is acceptable for paper; C2 should state which margin figure it feeds in
  (finding 5).
- It never raises available cash above the old formula's value or above cash: money-safe.

## Project rules

File sizes under 350; wiring only in `fno/composition.py` (`open_account_writer`, `build_paper_account`); book names
and ledger kinds in `fno/constants.py:28-35`; module file names as named constants at the top of their modules;
`WriterLock` protocol as the writer's interface; no order function; no secrets in the committed account files. One
duplicated enum noted (finding 4).

## Findings

1. **Minor. The lease adds a delay but no protection.** On one host the dead `flock` already proves the holder gone;
   between containers the lock file is git-ignored, so the lease never travels. Its only effect is that a crashed
   writer blocks its book for `DEFAULT_LEASE_SECONDS` = 600 s (`lock.py:33`). With fills due 15:15-15:20 (E3), a
   crash at 15:16 in the same container blocks a retry until 15:26. The story's wording asks for it, so not a fault
   of E1. Expected: E3 sets the lease to fit its timetable (or the story owner drops the lease rule).
2. **Minor, for E3/O1 (not E1's code).** The cross-container rule "pull, write under the lock, commit, push; if the
   push is rejected, pull and retry with the same fill IDs" will not work as written: two containers that each
   appended a fill to `cash_ledger.csv` (running `cash_after_rs` column) and rewrote `positions.json` get a merge
   conflict on `git pull --no-rebase`. The retry must first drop the local commit (`git reset --hard origin/main`),
   then re-apply the same fills. Expected: E3/O1 text and test say so.
3. **Minor. Equity history can rewrite any past day.** `record_equity(day, ...)` replaces the row for any date
   (`account.py:173`), not only today's. A late or mistaken call could silently change history the scoreboards read.
   Expected: refuse a day earlier than the last recorded day (or append-only with a correction row).
4. **Minor. `SIDES = ("buy", "sell")` in `fills.py:17`** duplicates the side values of `fno.accounting.ledgers.Order`;
   CLAUDE.md wants enum values in `fno/constants.py`. Expected: one constant, used by both.
5. **Minor, for C2.** State whether "margin blocked" is the broker's total margin (then a short option's value is
   counted twice in available cash, conservatively) or SPAN risk without option value. No E1 change needed.
