# Judge 227: BR1 follow-up after ChatGPT review 133 (judge A, lane 1, before S1's freeze)


Numbered 227: 225 and 226 were taken by other judges while this was written.
**Checked:** `story/br1-followup` at `6f49be48392ff82f7098036103250a2cc4854541` (from main 03705884). The claims are
response 231, and they apply response 230 (the orchestrator's answer to ChatGPT review 133, on main). The diff is 9
files, +134/−4.

**Verdict: PASS.** No blocking or should-fix findings; one note for the owner.

## (1) S1 hashes its freezer

- **The change:** `research/evaluation/PROTOCOL.md` `frozen_files` adds `fno/evaluation/definition.py`,
  `freeze.py` and `order.py` to the Files list. These are its only changed lines. The item's Status ("decided by the
  owner on 2026-10-14"), Reason and Evidence are untouched, and so is every other S1 item.
  `python -m fno evaluation check` on the trial merge still prints "PROTOCOL.md version 1: complete" and
  "REAL_MONEY_GATE.md: complete".
- **Does it keep to the item's own rule? Yes.**
  - The item's Reason is the owner's option A: "code written after decisions are seen could be shaped by them, so the
    code is hashed with its rules before anything is counted".
  - Since BR1a, `definition.py` carries S1's `requires_gate=True`, the real-money gate's link, and `freeze.py` and
    `order.py` decide what a freeze and a verify mean. Leaving them unhashed would let a later edit change a frozen
    version's meaning with no hash change, which is what the item exists to prevent.
  - The addition only strengthens the item, and it lands before S1's freeze. S1 is not frozen, so nothing frozen
    changes.
  - The precedent is DESK_DECISIONS row 106 (E8's code joined `frozen_files` "at the owner's request").
  - **Note for the owner:** this is a decided item's file list, changed at review 133's request without a new owner
    row. It is no weakening, so there is no fix, but the owner should see it in one line before S1's freeze.
- **Test:** `test_freezer_is_frozen.py` pins the three files in the real list. A fixture freezes a decided protocol
  listing `definition.py`, flips `requires_gate=True` to False, and `verify` reports "v1:
  fno/evaluation/definition.py changed after the freeze". My plant A (the real list misnames `definition.py`) fails
  1 test.
- **Note (no fix):** `fno/evaluation/wiring.py`, which maps the names to definitions, and `cli.py` stay unhashed. CI's
  verify uses `definition.py`'s `EVALUATION` directly, so an edit to either can change only a future freeze, which is
  a new version anyway.

## (2) The disclaimer and the `reporting` rule

- The disclaimer appears verbatim in all three `.md` files under `research/breadth/` (README, PROTOCOL, DIAGNOSTICS)
  and in response 198's Part 2, below the pre-declared Part 1, which is untouched.
- `PROTOCOL.md` `reporting` makes it the rule for "every BR1 chart, table and export", and says no family is ever
  marked as passing or as beating a baseline. That binds BR1b-BR1e's first outputs.
- `test_breadth_wording.py` checks the disclaimer in each file, the explanation sentence, and the absence of "PASS" or
  "beats baseline" in every BR1 `.md`. My plant B (DIAGNOSTICS' disclaimer cut short) fails 1 test.
- Leaving the committed study and candidate JSON files unedited is right: they are pre-registered outputs.

## (3) Dependence and skew; HAC parked

- The README, `null_size_check` and DIAGNOSTICS say "dependence is the leading supported explanation, with skew and
  tails contributing". That matches response 198's measurement (variance ratios of 1.43 and 2.08 for the `market`
  pairs) and ChatGPT's qualification.
- The README parks HAC or a stationary bootstrap as "only a future pre-registered version, never retrofitted", as
  response 230 point 4 says.

## Gates

- On the trial merge with origin/main 4c51747e (tree 771e81b, clean), `-n auto`: pytest 6914 passed.
- `ruff check` is clean, `ruff format --check` shows 1223 files formatted, and `check_imports` is clean.
