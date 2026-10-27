# Judge 121: NP9b follow-up (judge #2, code)

**Subject:** `story/NP9b-followup` at `a3e5c13` (on main `46321a7`).
- What it adds:
  - `text_rules.without_outlet` does its separator test on folded text, so a no-break space beside the separator counts
    as a space (judge 116's NBSP finding);
  - the `sources/model.py` docstring says why the unread rule fields stay (my judge 117 N1);
  - tests for my judge 115 Addendum 1 N1 and N2;
  - rows F21, F22 and F22b.
- Lane 1: `text_rules` is the frozen stored-title rule.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 1997 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 626 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

## Checks (*strong evidence*)

- **A frozen-rule change, but with no Record to revise.** No `manifests/news/` or `receipts/raw/news` exists on main, so
  no stored title changes and no re-poll records a revision.
- **The cut stays on the original title.** `fold` is one character for one, so cutting at `len(head.rstrip(...))` keeps
  the original characters. Reproduced:

  | Title (source) | Result |
  | --- | --- |
  | "Zzalpha rises - Zztv", and with the NBSP after the dash | "Zzalpha rises" |
  | "Zzalpha's rise - Zz's Post", curly apostrophes | the curly apostrophe is kept |
  | "Rally as Zztv" | kept whole (no separator) |
  | "Zzalpha - Zztv" | "Zzalpha" |

- **My plants:**

  | Plant | Mutation | Result |
  | --- | --- | --- |
  | N1 | the version 1 matcher drops the source | **now caught** (2 failed) |
  | N2 | the version 2 preparer drops the source | **now caught** (2 failed) |
  | N3 | the NBSP fold removed from the separator test | caught (2 failed) |

  Judge 115's test gap is closed.

**Verdict: PASS** (round 1, `a3e5c13`).

**Note on my own index entry:** my first push of this verdict (`478dcb5`) added a broken row to `README.md`, with no
number and no file, because of an error in my script. This commit corrects that row and adds this file.

## Addendum 1

**Re-confirmation at `a0697e3`.** It is the `a3e5c13` I passed, plus main merged in (NP10), plus one docstring word in
`sources/model.py` (judge 1's N1).
- Against main, the diff is NP9b's own content only: `text_rules.py`, `sources/model.py`, `test_matching.py`, the
  stored-title test and plants F21, F22 and F22b.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 2010 passed.
- `ruff check`: clean.
- `check_imports`: 628 files clean.
- `check_numbers`: clean.
- **The full plant runner: 274 of 274 `ok`.**

**Verdict: PASS** (`a0697e3`).
