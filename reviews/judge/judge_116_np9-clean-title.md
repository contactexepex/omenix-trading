# Judge 116: NP9 clean stored title (code), round 1 at ed90a5c: FAIL (one regression)

**Lane 1, two judges; this is judge #1.** Branch `story/NP9-clean-title`, frozen SHA ed90a5c (its code is the same as 302f65f). I reviewed `git diff origin/main...ed90a5c`, which touches:
- `news/text_rules.py` (new);
- `article/article_file.py`;
- `tagging/text.py`, `tagging/tagger.py` and `materiality/terms.py`;
- the tests, the plants, and the contract section "The stored title (NP9)".

## Gates (strong evidence)
In a venv installed from `requirements.lock`:
- 2028 passed;
- ruff check is clean, and check_imports is clean;
- **plant runner: 280 of 280 `ok`**, nothing unnoticed.

## B1 (required; strong evidence, run on both trees): moving `fold` lost the no-break-space mapping
- On `main`, `_QUOTES` in `tagging/text.py` maps U+00A0 (bytes `302 240`) to a space. In `text_rules.py` the same entry is now a **plain space mapped to a space** (bytes `" ": " "`), because the character was lost when it was copied.
- **Measured:**
  - `main`: `fold("a b") == "a b"`;
  - the branch: `fold("a b") == "a b"`.
- **Effects:**
  - **The stored title (new, and frozen by this story).** `"Rates rise - Outlet"` is stored as `"Rates rise - "`, with a dangling dash and a no-break space, where `main`'s tagger path gave `"Rates rise"`. Once this rule is frozen, fixing it later records a revision on every re-poll in the window.
  - **Tagging and materiality.** `capped()` and `plain_text()` stop folding no-break spaces, so a company name or term with a space no longer matches text that uses a no-break space. That changes behaviour silently in code the story says it leaves alone.
- **Docstring.** It still says "no-break spaces folded".
- **Unpinned.** No test uses U+00A0 (searched `tests/ingestion/news`), so the full suite and the runner both stay green with the regression in place.
- **Fix:**
  - write the entry as `" ": " "`, an escape so it cannot be lost again;
  - add a test that `fold("a b") == "a b"`;
  - add a stored-title test where a no-break space sits next to the separator;
  - add a plant on that `_QUOTES` entry.

## My conditions from judge 111: met
- **(1) Frozen rule.** The `text_rules.py` docstring says the rule is part of the Record's bytes, and that changing it is a lane 1 Record change (a format bump or a stated revision note). The contract section points at it.
- **(2) The empty guard.** `without_outlet(...) or title` keeps `"- Outlet"` whole. The helper itself still returns `""` there, but the store never uses an empty result (row F17).
- **Neutral module and case-insensitive tail.** The match is now `fold(title)[-len(name):].lower() == name.lower()`, and the cut is on the original title (length-safe, because `fold` is one character for one).

## What holds
- **The key is unchanged.** `item_key` still reads the raw item, and only `title=` changes.
- **Wrappers only.** A publisher title is stored exactly as given.
- **The tagger and materiality** import `without_outlet` from the neutral module, and their behaviour is unchanged apart from B1.
- **Format 2 is kept**, which is right for an empty Record (judge 111).

## Hard lines
No orders, no Groww, no secret. No title in any log.

## Verdict: FAIL round 1 at ed90a5c. B1 required: restore the U+00A0 fold with an escape, a test and a plant.

## Addendum 1: round 2 at 7406cba: PASS, with one stated limit

I reviewed `git diff ed90a5c 7406cba`. It covers the `text_rules.py` escape, judge 115's B1 (`title_form(title, source)` in `cluster/`), tests, and rows F18 to F20.

**Gates (locked venv, strong evidence).**
- 2030 passed.
- ruff check is clean, and check_imports is clean.
- **Plant runner: 283 of 283 `ok`.**

**B1, the regression: fixed (strong evidence, run).**
- `_QUOTES` now reads `" ": " "`, so `fold("a b") == "a b"`, as on `main`. Tagging and materiality are back to `main`'s behaviour.
- The implementer also compared every code point against `main`'s `fold` and found no differences; I did not repeat that.
- F20 and its test pin the fold.

**What is still open (strong evidence, run; a limit, not a regression).**
- The new test puts the no-break space **inside** the outlet name (`"Daily Ledger"`). That case works.
- My round-1 case had it **next to the separator**, and it still leaves a tail on the stored title:
  - `"Rates rise - Outlet"` is stored as `"Rates rise - "`;
  - `"Rates rise - Outlet"` is stored as `"Rates rise "`.
- The cause: `head.rstrip(_SEPARATORS)` runs on the original text, and U+00A0 is not in `_SEPARATORS`.
- **Why I accept it now (reasoning only, with the downstream checks run):**
  - Downstream is unaffected. `title_form` on that title gives `"rates rise"`, and the tagger path (`capped` then `without_outlet`) gives `"Rates rise"`.
  - So only the stored text carries a cosmetic tail, and only on titles with a no-break space beside the dash. I believe that is rare in Google News feeds, but it is unmeasured.
  - Fixing it later records revisions only for those rare items, not for every re-poll.
  - This is round 2, the last.
- **Requested follow-up (lane 1, small):** compute the cut index on the folded title and apply it to the original. For example: `cut = len(fold(head).rstrip(_SEPARATORS)); return title[:cut]`. It is length-safe because `fold` maps one character to one. Add a row with both cases, and state in the contract section that re-polls of affected items will record revisions. **Better done before the first real promotion,** while the Record is still empty and the fix costs nothing.

**Judge 115's B1: fixed.** Clustering now cuts only a tail that is the feed's own `source`, so a headline's own " - profit rises" stays. Rows F18 and F19 pin it, including two opposite stories that must stay apart. The Record has no cluster files yet, so changing the title form needs no version bump.

**Verdict: PASS round 2 at 7406cba.** The no-break-space-beside-the-separator limit is stated, and its fix is requested before the first real promotion.
