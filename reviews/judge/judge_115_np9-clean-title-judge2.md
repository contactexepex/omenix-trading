# Judge 115: NP9 clean stored title (judge #2, code)

**Subject:** `story/NP9-clean-title` at `ed90a5c` (the implementer says the code is identical to `302f65f`).
- What it does:
  - a new neutral module `news/text_rules.py` holds the frozen `without_outlet` and `fold`;
  - `build_article` strips the trailing " - Outlet" from a Google News (wrapper) title, only when the tail equals the
    item's source;
  - the key still comes from the raw item;
  - an empty-title guard.
- Rows are in the RECORD_CONTRACT. Lane 1: it changes stored Record bytes.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 2028 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 638 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

## What holds (*strong evidence*)

- **No false revisions.** The key is computed from the raw item (`item_key(kind, item, published)`, before the title
  is cut), so it is unchanged. No article file exists on main (no `manifests/news/articles.csv`), so no stored title
  changes meaning.
- **The cut is narrow.** Only wrapper items, and only a tail equal to `item.source` after whitespace and a separator.
  `or title` keeps a title that would become empty.
- **The move is behaviour-neutral for the tagger and the terms.** `without_outlet` moved verbatim except that the match
  now runs on `fold(title)`. `fold` is one character for one, so the slice is the same length. It is idempotent on a
  clean title.

## Blocking

1. **B1: clustering now cuts real headline text from Google News titles** (*strong evidence*, reproduced at
   `ed90a5c`).
   - The story says (lines 45 to 47) that clustering "no longer has to guess a tail". It does still guess.
     `cluster/title_text.py::_without_outlet` is a BLIND heuristic: it cuts the text after the LAST " - ", " – ", " — "
     or " | " when the tail has at most 4 words and the head at least 3. It does not check the source.
   - Before NP9, that last separator was the outlet's. After NP9 the outlet is gone, so the heuristic eats the last
     segment of the HEADLINE.
   - Reproduced with `title_form` (invented names):

     | Raw Google News title | Form before NP9 | Form after NP9 |
     | --- | --- | --- |
     | "Zzalpha Q2 results - profit rises 20% - Zztv Profit" | `zzalpha q2 results profit rises 20` | `zzalpha q2 results` |
     | "Sensex falls 500 points - what investors should know - Zztv Profit" | `sensex falls 500 points what investors should know` | `sensex falls 500 points` |

   - **Effect:** "Zzalpha Q2 results - profit rises 20%" and "Zzalpha Q2 results - profit falls 5%" now have the SAME
     form, Jaccard 1. Both version 1 and version 2 would merge them into one story in the write-once cluster record.
     Indian headlines use an inner " - " or " | " often, as in "Stocks to watch | ..." (*reasoning only*, unmeasured).
   - **Fix:** clustering must not blind-trim a title the Record has already cleaned. One way is to trim with
     `text_rules.without_outlet(title, article.source)` instead of the heuristic. Then:
     - a wrapper title is untouched;
     - a publisher title loses only a tail that equals its own source.
   - Either way, state in the story how this changes version 1's algorithm (there are no files yet, so nothing old to
     reproduce). Add a test and a plant with a headline that holds an inner " - ".

## Notes (not blocking)

- **N1: wire detection.** `OriginReader` (parked, no caller) found a wire through a title ending "- Agency". For a
  wrapper whose outlet IS the agency, the stored title no longer carries it. The domain and provider routes still work
  once resolved.
  - Record this in the parked-code note, so the keep-or-delete decision sees it.
- **N2: the raw title cannot be rebuilt exactly.** The story says this plainly ("title + ' - ' + source rebuilds the
  usual form but not always the exact original"). I agree a `raw_title` field is not needed.

**Verdict: FAIL** (round 1, `ed90a5c`). B1 is a regression in what the clustering records, and the fix is small.
