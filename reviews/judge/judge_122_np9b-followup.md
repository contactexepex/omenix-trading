# Judge 122: NP9b follow-up (code), round 1 at a3e5c13: PASS

**Lane 1; judge #1.** Branch `story/NP9b-followup`, frozen SHA a3e5c13, based on `main` 46321a7. I reviewed `git diff origin/main...a3e5c13`: `text_rules.py`, the `sources/model.py` docstring, the NP1 doc, tests, and rows F21, F22 and F22b.

## Gates (strong evidence)
In a venv installed from `requirements.lock`:
- 1997 passed;
- ruff check is clean, and check_imports is clean;
- **plant runner: 262 of 262 `ok`.**

## My judge 116 limit is closed (strong evidence, run)
`without_outlet` now folds the head and cuts the original title at the folded length. That is length-safe, because `fold` maps one character to one.

| Title, with source `"Outlet"` | 7406cba | a3e5c13 |
|---|---|---|
| `"Rates rise - Outlet"` | `"Rates rise - "` | `"Rates rise"` |
| `"Rates rise - Outlet"` | `"Rates rise "` | `"Rates rise"` |
| `"Tata’s up - Outlet"` | `"Tata’s up"` | `"Tata’s up"` (the headline's own quote is kept) |
| `"- Outlet"` | `""` | `""` from the helper; `build_article` still keeps the original title (F17) |

- Row F21 and its plant pin it.
- The Record still has no news receipts, so changing the frozen rule now records no revision. The rule's docstring states the frozen-rule note.

## Judge 115's note
Rows F22 and F22b pin that the matcher and the version 2 preparer pass `article.source` to `title_form`.

## Note (not blocking)
- **N1, a docstring that is inaccurate.** The new `sources/model.py` docstring lists `same_as` among the "fields no code here reads", but `SourceRules._allows_fetch` reads `outlet.same_as` (`main = self.outlets.get(outlet.same_as)`), and `may_fetch` depends on it. Drop `same_as` from that list in the next small commit, so no later clean-up removes a field the fetch rule needs.

## Hard lines
No orders, no Groww, no secret. No title in any log.

## Verdict: PASS round 1 at a3e5c13. N1 requested.

## Addendum 1: the reconciled head a0697e3: PASS

a0697e3 is a3e5c13 plus a merge of `main` (NP10, b5787b2) plus my N1.

**The changes.**
- `text_rules.py` is the same as at a3e5c13.
- N1 is fixed: `same_as` is no longer listed among the "fields no code here reads", because `may_fetch` uses it.
- Against `main`, the branch's net change is NP9b alone: 5 files in `fno/`, `tests/` and `tools/`, with F21, F22 and F22b as the only new plants.

**Gates at a0697e3 (locked venv, strong evidence).**
- 2010 passed.
- ruff check is clean; check_imports is clean.
- **Plant runner: 274 of 274 `ok`.**

**Verdict: PASS at a0697e3.**
