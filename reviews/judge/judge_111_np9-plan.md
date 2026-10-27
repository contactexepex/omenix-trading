# Judge 111: NP9 clean stored title (plan doc), round 1 at d346ece: PASS, on two text conditions

**Lane 1 plan, sole judge (judge #1).** Branch `story/NP9-plan`, frozen SHA d346ece: one file, `docs/stories/NP9-clean-stored-title.md` (58 lines). I checked the claims against `main` (at the time of review).

## Claims checked
- **"Zero migration": confirmed (strong evidence, in the repository).**
  - `research/data/manifests/news/` does not exist.
  - `find receipts -path '*news*'` finds nothing.
  - So no article file has been receipted. Every Record write goes through the write-once writer, which receipts it, so no article file exists whose title meaning would change.
  - Keeping `format: 2` without a bump is therefore right.
- **The key stays raw.** `build_article` computes `item_key(kind, item, published)` from the raw item (`article_file.py:50`). Cleaning only `title=` leaves the key alone.
- **Re-polls stay stable.** `fixed_fields` is every field except `first_seen_at`, and the manifest records one revision per (article id, SHA-256) (`record/manifest.py`). A pure cut of two strings gives the same bytes on every re-poll, so no false revision appears.
- **The helper exists, with a gap (strong evidence, run).** `tagging/text.py` `without_outlet` cuts only after a separator from `" -–—|"`. But today it **empties** a title that is only a separator and the outlet:
  - `without_outlet("- Outlet", "Outlet") == ""`;
  - `"Outlet"` alone is kept;
  - `"Rates rise | | Outlet"` becomes `"Rates rise"` (all trailing separators stripped).

  The plan's row "a title that is only the outlet is not emptied" is right, but the helper does not meet it yet. The code must add the guard, and the test must use the `"- Outlet"` form.
- **Fold length.** `fold` maps three characters one to one (two curly quotes and the no-break space), so comparing on the folded text and cutting the original by the same index is length-safe. Do not compare with `.lower()` on the whole title, as the helper does now. Compare `title[-len(name):]` case-insensitively instead, so a lower-casing that changes length can never shift the cut. That is reasoning only: a rare Unicode case.

## Open point (7): the neutral module (reasoning only, with one consequence that decides it)
I choose the **neutral module**, for example `news/text_rules.py` holding `fold` and `without_outlet`, imported by both `article/` and `tagging/`. Importing from `tagging/` would make the Record's builder depend on the tagger. The deciding reason is not layering taste, though:

**The cleaning rule is now part of the Record format.** If the shared helper changes later, for tagging's sake, every re-poll of an item still in the feed window gets a different title. The manifest then records it as a **revision**: a new write-once file per item, with no real change in the news. So the store rule must be one place that is owned and pinned, not a tagging utility.

## Conditions (text, in the plan before code)
1. **The rule is frozen.** State that the stored-title cleaning rule is part of the article format: a change to it is a lane 1 Record change and needs a format bump or an explicit note that re-polls will record revisions. Point the contract rows at the neutral module.
2. **Name the empty-title guard.** `"- Outlet"` must stay `"- Outlet"`, or at least never become `""`, and the planned row's test must use that input.

## What holds
- **Conservative cut.** The suffix is cut only when it equals the item's own `source`. A "- The Hindu" suffix on a "The Hindu BusinessLine" source is kept and said plainly.
- **Anti-spoof.** Cleaning removes a claim and verifies nothing. The verified publisher stays the resolved host (NP2c).
- **No `raw_title` field.** The loss (the separator and the outlet's spelling) is stated, and `source` keeps the outlet. I agree; reasoning only.
- **Scope (the owner's ingestion-only rule, now in CLAUDE.md):** this is what the Record stores; it touches no consumer.
- **Downstream.** Tagging, materiality and clustering call the helper again and it is idempotent on a clean title. The possible change to clustering merges is stated, and NP3c can measure it.

## Hard lines
No orders, no Groww, no secrets. No title is printed in any log.

## Verdict: PASS round 1 at d346ece, on conditions 1 and 2 (text; the orchestrator can check them). For open point (7): the neutral module.
