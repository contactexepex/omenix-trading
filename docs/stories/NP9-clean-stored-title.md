# NP9: the stored title is the clean headline (PLAN)

PLAN for the orchestrator's check and one judge before any code. Lane 1 for the code that follows (it changes the content of the
write-once Article Record). Owner decision relayed by the orchestrator, 27 Oct 2026: the title stored for a Google News item must be the
clean headline, with the " - Outlet" suffix Google News appends removed at ingestion. **This document builds nothing.** Scope rule: this is
ingestion (what the Record stores), nothing about a consumer.

## What changes (about 15 lines of code)
1. **`build_article`** (`article/article_file.py`): for a Google News item (kind `wrapper`), `title = without_outlet(item.title.strip(),
   item.source.strip())`. A direct publisher item has no suffix and is left as it is. The helper already exists
   (`tagging/text.py`, NP5a, tested); it is reused, not copied (DRY). Importing it from the article package is a layering smell (the article code
   would depend on the tagging package); the alternative is moving the helper and `fold` to a neutral module. Reasoning only: the import is
   simpler, the move is cleaner; the judge may choose.
2. **The helper gets one fix** it needs for storing (it did not matter for tagging): it compares on the folded text (typographic quotes and
   no-break spaces made plain, character for character) but cuts the ORIGINAL title, so an outlet whose name has a curly apostrophe still matches and
   the stored title keeps its own characters. Today `without_outlet` is handed an already folded title, so the tagger and the materiality terms
   behave exactly as before (their tests stay).
3. **Where the suffix is cut:** only when the title ends, after a separator (`-`, an en or em dash, or `|`) and a space, with the item's own
   `source` text, ignoring case. A suffix that does not equal the source (for example the feed's source says "The Hindu BusinessLine" and the title
   ends "- The Hindu") is NOT cut: the title keeps it. How often that happens is unmeasured; the tagger, the terms and the clustering still trim a
   residual suffix by their own rules, so nothing breaks, the stored title is just not clean for those items.

## What does not change
- **The key.** `item_key` is computed from the RAW item (guid, else time + normalised raw title + summary + source), as before, so the key
  never depends on the cleaning (NP0 N2 holds: a key never changes). A re-poll of the same item gives the same key and the same cleaned title:
  the cut is a pure function of two strings, so the revision comparison (`fixed_fields`) finds no difference and no false revision is recorded.
- **The format.** Article files stay `format: 2`. Reasoning for no bump, with the evidence: nothing has been promoted yet (the repository has no news
  manifest and no news receipts), so no file exists whose title meaning would differ. The field comment in `Article` and the P2b story say the title
  of a Google News item is the cleaned headline. The judge should confirm this reading of "zero migration".
- **The outlet is not a new field.** The outlet label is already stored as `source` (the feed's own `<source>` text) and its host as
  `source_domain`.

## Anti-spoof, stated plainly
The suffix removed is the feed's CLAIMED outlet (`source`), a hint. The verified publisher stays the host of the resolution file (NP2c). The cut
happens only where the suffix equals the claim, so cleaning never implies the outlet is verified; nothing downstream may take `source` as proof
(the view and tier code already use the resolved host or the item's own link).

## What is lost (said plainly)
The raw title of a Google News item is not kept in the Record. After the staged poll is cleaned (S1), the removed text is gone: the separator
character (`-`, a dash or `|`) and the exact spelling of the outlet in the title. The outlet itself stays in `source`, so `title + " - " + source`
rebuilds the usual form but not always the exact original. I judge that acceptable (reasoning only: nothing the pipeline does needs the raw
form). The alternative, a `raw_title` field, needs a format bump and doubles a field for no use I can name; not recommended.

## Downstream effects
Tagging, materiality and clustering call `without_outlet` again on titles; on a clean title it does nothing (idempotent), so their results do
not change except where a suffix used to remain and the old rules mishandled it. Clustering shingles for Google News items become cleaner (the
title heuristic in `cluster/title_text.py` no longer has to guess a tail), which can change merge results; the version 1 against version 2
comparison (NP3c) is unaffected as both see the same stored titles. The planned tests pin each of these.

## Contract rows planned (docs/RECORD_CONTRACT.md, new section "The stored title (NP9)")
A Google News title is stored without its trailing source; a publisher title is stored as given; a suffix that is not the item's source is kept;
the key does not depend on the cleaning; a re-poll gives the same bytes; the helper matches a curly-apostrophe outlet and keeps the title's
own characters; the cut needs a separator (a title that merely ends with the source's word keeps it); a title that is only the outlet is not
emptied. Each with a plant, and the full plant runner green at the final SHA.

## Size and order
About 15 lines of code, one helper fix, tests, three doc lines (the P2b story, the `Article` field comment, the contract section). Lane 1,
two judges for the code after the plan passes.

## Judge 1 PASS conditions and the final design (27 Oct 2026)

- **Neutral module (decision 7):** `without_outlet` and `fold` live in `fno/ingestion/news/text_rules.py`; article, tagging and
  materiality import from it. Reason (judge 1): the cleaning rule is part of the Record's format; tuning the tagger must never
  change stored bytes.
- **The stored-title rule is frozen.** A change to `without_outlet` is a lane 1 Record change: a format bump, or a stated note
  that re-polls will record revisions. Stated in the module docstring and in the "The stored title (NP9)" section of
  `docs/RECORD_CONTRACT.md`.
- **Not-emptied guard (row F17):** `without_outlet("- Outlet", "Outlet")` returns `""` (judge 1 ran it); the helper stays as it is
  for the tagger, and `build_article` guards it with `... or title`, so a title the cut would empty is stored as given.
- **Match (judge 1 suggestion):** compare `fold(title)[-len(name):]` to the name case-insensitively, not `.lower()` on the whole title.
- Rows F14, F15, F15b, F16, F17 with plants; T16 and T17 re-pointed to `text_rules.py` (T17 follows the new match line).

## Code judges, round 1 (judge 115, judge 116) and the fixes

- **Judge 116 B1 (my regression in the move):** `_QUOTES` lost its U+00A0 entry (a no-break space typed as a plain space). Fixed with
  the escape `" "`; row F20 with a plant; a test with a no-break space inside the outlet tail.
- **Judge 115 B1 (an interaction I missed):** `cluster/title_text.py` cut the last " - ..." of every title with a blind heuristic
  made for titles that still carried an outlet; on clean titles it ate real text ("Q2 results - profit rises 20%" and "... profit
  falls 5%" became one form and merged). Fixed by using the shared `without_outlet(title, article.source)`: only a tail that IS the
  outlet the feed named is cut. This changes the clustering algorithm (versions 1 and 2 share `title_form`); no cluster files exist
  yet (the Record is empty). Cost, said plainly (reasoning only): a publisher item whose feed names no `source` keeps a trailing
  " - Outlet" in its form, so a wrapper/publisher pair of one story scores a little lower; `news compare-clusterings` measures it on
  real data. Rows F18 and F19 with plants. The parked-code note on agency wrappers (judge 115 N1) is moot: DEL1 deletes that code.
