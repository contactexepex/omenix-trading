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
