# Judge 134: C5b story text, a brake restart cites the owner's decision row: `story/c5b-restart-decision` a29778d83c0bcf3a31508dacd004157ed5bf7ec5 (quality rule 1, text only; judge A)

**What I checked:**
- the C5b section of `docs/stories/C-code-roles.md`, the only story change;
- `fno/risk/overrides.py` on `main`;
- the committed `docs/DESK_DECISIONS.md`, against the five rules the story writes. That file is the real input of
  every check, so I tested the rules on it.

## Is the design sound? YES

- **The design.** A fifth `decision` column cites one `DESK_DECISIONS.md` row. The row must:
  - exist exactly once;
  - quote the owner;
  - name the book;
  - be dated on or before the restart;
  - not be reused.
  C2 and C4 each check it with their own code and fail closed, plus a JUDGE.md audit.
- **It closes judge 105 minor 3's real gap.** Today a typed `entered_by: owner` is all a restart needs.
- **Cost of the format change: none.** No book has an `owner_overrides.csv` yet: `journal/` holds `book1_rules`,
  `book2_hybrid` and `book3_ai` with no overrides file.
- **"That episode" is left to the audit, and that is right.** A code rule for "episode" would need a brake history
  model; the dated, not-reused rule covers the mechanical part.
- **No cryptography,** per the owner's simplicity rule. The known limit (anyone who can commit can add a row) is
  stated in one line.

## Tested against the real `docs/DESK_DECISIONS.md` (152 dated table rows)

| Story's rule | Real file | Effect |
|---|---|---|
| Criterion 3: "every table row yields a date and a **title**" | **17 of 152 dated rows have no bold span at all.** Examples: "Shared goal", "D5 approved: Claude may not change trading rules on its own", "Repository stays `exepex/trading` for now (owner: "no for now")" | Criterion 3 as written fails on the committed file. The builder would have to bend it, or the parser would refuse the real file and fail every book closed |
| "the exact bold title of the cited row" | **4 rows of 12 Oct put a bold word inside the text, not a title.** "Design section 12 **approved**", "Clean-slate design v2.1 **approved**; ... **deleted**", and two more. "approved" occurs as a bold span in 4 rows | The "exists exactly once" rule makes such a title uncitable, which is safe. But the story must say which bold span is the title (the first one in the Decision cell) and that rows without one are not citable |
| "names the restarted book" | Books are named **"Book 1" (10 rows), "Book 2" (2), "Book 3" (2)**, never by their IDs (`book1_rules`, `book2_hybrid`, `book3_ai`, `fno/constants.py:38-41`) | Undefined matching. If the code matches the folder ID, the owner's real restart row ("restart Book 1", written like every other row) fails closed, and the brake can never be lifted by a real decision. That changes a trade decision |
| `(owner: "` | 91 of 152 rows carry it; the rest quote the owner in other forms ("Owner: ...", `("accept")`) | Fine for new rows, which the orchestrator writes in the standard form. Say so in one line, so the form is known when the owner's restart is recorded |

## Should-fix (text)

1. **Define the citable title, and fix criterion 3.**
   - The title is the **first** `**...**` span in a row's Decision cell. A row without one is not citable.
   - Criterion 3 becomes: "the committed file parses: every dated row yields its date. N rows have a citable title. A
     title that occurs twice (e.g. 'approved', in 4 rows) is refused by the exists-once rule".
   - Evidence: 17 untitled rows, and a bold "approved" in 4 rows, in today's file.
2. **Define how a row "names the book".**
   - Accept the book's display name as the decisions file writes it: `Book 1` for `book1_rules`, `Book 2` for
     `book2_hybrid`, `Book 3` for `book3_ai`. Map the names in one place in `fno/constants.py`, and match them as whole
     words.
   - Test that a real-style row "restart Book 1" lifts `book1_rules` and does not lift `book2_hybrid`.
   - Evidence: every book mention in the file is "Book N"; none uses the ID.

## Note (one line)

- State that a restart decision row is recorded in the standard form `**title** (owner: "...")`: 61 of today's rows
  use other quote forms.

### Verdict: FAIL for a29778d83c0bcf3a31508dacd004157ed5bf7ec5 (story text)

- **Two should-fix, both text:** the title definition (with criterion 3), and the book-name match.
- **Why they matter:** both are real-data defects. Built literally, one would refuse the committed file, and the other
  would refuse the owner's real restart.
- **A re-check needs only the C5b section.**

## Addendum 1 (15 Oct 2026): revision 2 at 8a7f185c4cb4bc3c3377eb667e89340d58d2c1b9 (text only; claims renumbered to response 135)

| Judge 134 finding | Status | Check |
|---|---|---|
| Should-fix 1: the citable title, and criterion 3 | MET | The title is the first `**...**` span of the Decision cell. A row with no bold span is not citable. A title repeated in the file is refused. Criterion 3 now counts rows, untitled rows and repeated titles against the committed file |
| Should-fix 2: "names the book" | MET | `BOOK_DISPLAY_NAMES` in `fno/constants.py` (`book1_rules` → "Book 1" and so on), matched as a whole word, so "Book 1" is not "Book 10". C4 reads the map from constants, not from C2's code, which keeps C4 independent. Criterion 2 adds the test "Book 1 lifts `book1_rules`, not `book2_hybrid`" |
| Note: the standard form | MET | The restart decision is written as `**title** (owner: "...")`, and the test fixtures use that form |

**One slip in the context line, a note only.** It says the title "approved" "appears twice". On today's file, using the
story's own rule (the first bold span of the Decision cell), "approved" is the title of **4** rows (152 dated rows).
Criterion 3's test counts against the committed file, so the built test will carry the true number. Correct the text
when next touched.

### Verdict: PASS for 8a7f185c4cb4bc3c3377eb667e89340d58d2c1b9 (story text)

Both should-fix items are met. Code may start.

## Addendum 2 (judge C, 15 Oct 2026): C5b code at b2a4b0dd322c29b639d2b07530491e5bab173b0e

Date: 15 Oct 2026 (UTC). Branch `story/c5b-restart-decision` at **b2a4b0dd322c29b639d2b07530491e5bab173b0e**.
- Claims: response 135 addendum 2.
- The story text was passed by judge A (judge 134 addendum 1).
- Judged on the real paths, under the owner's "keep the design simple" rule.

### Gates

- `env -u FNO_SLACK_BOT_TOKEN python -m pytest -q`: **5,468 passed** (the builder's figure).
- ruff check, format and `check_imports.py` are clean.
- `merge-tree` with `origin/main`: no conflict.

### Verdict: PASS (code)

| Real path | Status | Evidence |
|---|---|---|
| A restart counts only with a citation | MET | C2 (`fno/risk/decision_rows.py`, called from `overrides.brake_restarts`) and C4 (`fno/checks/validity_decisions.py`, called from `LedgerAccounts.facts`) each read `docs/DESK_DECISIONS.md` themselves. The cited title must be the first bold span of exactly one dated row, and that row must hold `(owner: "`, name the book as a whole word and be dated on or before the restart. A title may be used once per book. Any failure raises (C2 `RiskInputError`, C4 `AccountProblem`), so the brake stays on: fail closed |
| "Book 1" never matches "Book 10" | MET | `\bBook 1\b` finds no word boundary between `1` and `0` |
| C4 independent of C2 | MET | C4 has its own regex and parser, with no `fno.risk` import |
| Existing data | MET | No `owner_overrides.csv` exists on `main` (`git ls-tree` on origin/main), so the new `decision` column breaks no stored file |
| The audit step | MET | `docs/JUDGE.md` "Brake restarts": every override-row change is lane 1, and the judge reads the cited row and confirms the owner's own words restart that episode |

### The orchestrator's two points

- **Criterion 3's minimums (at least 152 rows, at least 17 untitled, at least 4 "approved"): accepted.**
  `DESK_DECISIONS.md` is append-only, so exact counts would break on every new owner row. The real check is that the
  parser's titles equal a second, independent count by splitting on `**`, row for row
  (`test_validity_restart.py:64`, `test_restart_decision.py:72`). The minimums only guard against the parser reading
  nothing.
- **Shadow-book brakes cannot be lifted: agreed for now.** `BOOK_DISPLAY_NAMES` holds Books 1-3 only, so a shadow's
  restart is refused by name (fail closed). Shadows are research records that never trade money. If a shadow ever needs
  its brake lifted, that is an owner decision and a story.

**Note (does not change a trade):** the book must be named exactly "Book 1", "Book 2" or "Book 3" in the owner's row.
A row saying "all books" or "book 1" in lower case is refused (fail closed, the reason names it). The owner or the
orchestrator then words the row with the book's name.

**Verdict: PASS for b2a4b0dd322c29b639d2b07530491e5bab173b0e** (code). Rule 9: ChatGPT next.

## Addendum 3 (judge C, 15 Oct 2026): re-check at 305a4851ef89e8955619b0a563f7097abdbe27dc

The base is my PASSed b2a4b0d plus two merges:
- 1b9b7b30: `origin/main`, and a `docs/JUDGE.md` line;
- 305a4851: `story/e1b-journal-pin` dde9470, judged by judge A.

| Check | Status | Evidence |
|---|---|---|
| Both behaviours survive the import conflict in `fno/checks/validity_account.py` | MET | The merged file imports `DESK_DECISIONS_FILE`, `LEDGER_TOP_UP` and `decision_problem`/`decision_rows`. It defines `TRADE_KINDS` and `CAPITAL_KINDS`. `account_facts` counts capital from the opening plus top-ups by the cutoff (lines 119-126), and `restart_days` still calls `decision_problem` (line 147). `test_validity_restart.py`, `test_validity_top_up.py` and `test_validity_capital.py` are all in the green suite |
| Gates | MET | 5,700 passed (the builder's figure); ruff, format and imports clean; `merge-tree` with `origin/main`: no conflict |
| The new `docs/JUDGE.md` line | accepted, with one plain consequence | "The judge also confirms the words with the owner directly ... no answer is a FAIL." No person types in a judge session that the orchestrator starts, so I cannot get the owner's yes myself. Under this rule, every brake restart judged in such a session is a FAIL until the owner answers in a judge session. It fails closed and is safe, but the owner should know a restart needs them to answer a judge directly |

**Verdict: PASS for 305a4851ef89e8955619b0a563f7097abdbe27dc.**
