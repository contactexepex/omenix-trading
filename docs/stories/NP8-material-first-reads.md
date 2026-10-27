# NP8: the read pass reads the material headlines first (PLAN)

PLAN for the orchestrator's check and one judge before any code. Lane 1 for the code that follows (it makes a run read the owner's two private
files and adds a new write-once Record file). Plan: [NP0](NP0-news-port-plan.md) section 2h and [NP4](NP4-page-reads.md); raised by the
implementer while planning NP7 and accepted by the orchestrator. **This document builds nothing.**

## The gap, verified in code
`ReadPass._candidates` (`reads/run.py`) sorts the Record's articles newest first and takes the first 80 whose page may be fetched. NP4's plan
said the pass would prefer "material" headlines once NP5 existed. NP5 built `Tagger` and `MaterialTerms`, but nothing in `reads/` imports them
(checked by search), so the owner's materiality file, once written, would change no run: the 80 pages a pass goes to whatever came last.
**Until NP8 lands the read pass is newest first and materiality has no effect.** (Evidence: the code. How often that matters on real
news is unmeasured: reasoning only.)

## What it builds
1. **A `ReadOrder` strategy behind the pass** (one new class per order, one line in the composition root): `NewestFirst` (today's behaviour,
   unchanged) and `MaterialFirst(tagger, terms)`. `MaterialFirst` ranks in two tiers: (1) material articles (`MaterialTerms.is_material`:
   weight at least 1 AND exactly one company named in the title with high confidence), (2) all others; newest first inside each tier, so the
   ranking is deterministic. This is the orchestrator's scope ("material, high-confidence, single-company first; then the rest"); a finer
   ranking (weight order, medium confidence) is not planned (KISS; reasoning only that two tiers are enough to start).
2. **How the pass uses it.** Today the pass reads Record files only to find each page's URL, and stops choosing at 80 pages. Ranking needs each
   candidate's title and source, so the pass first reads the article file of up to `MAX_RECORD_READS` (400) newest unread articles, ranks them,
   and then resolves URLs (a resolution file read for a Google News item; the unlisted and unresolved ones are counted and skipped) down the
   ranking until 80 pages are found. **Consequence, stated plainly: the ranking is applied inside the newest ~300 to 400 articles, not over the
   whole 3-day look-back.** At about 1,500 articles a day (agentic's count, strong evidence for its own feeds) that slice is roughly the last six
   hours, so a material headline is read only if a pass runs within about that time after it was recorded. The slice size is the real lever:
   raising `MAX_RECORD_READS` costs Drive reads and run time, both unmeasured. The plan does not change it.
3. **Which files the pass reads and what happens when they are missing (the orchestrator's rule, stated for the judge).**
   - No materiality file configured (`materiality_missing`), or no company list configured (`company_list_missing`): the pass falls back to
     `NewestFirst` (degraded but working) and says so in its line (`order newest_first`). Without a list nothing can be tagged, so nothing
     could be material anyway.
   - A file that EXISTS but cannot be used (invalid, rolled back, edited in place, damaged, or the store unreadable): the pass STOPS, writes
     nothing and is red, like the company-list rule of NP7b. Not a fallback: a silent newest-first would hide that the owner's file is broken.
4. **The SHA and rollback rule is carried here** (the materiality file is first read in this story): a pass that writes (`apply`) also writes a
   small **write-once pass note** `news/read-passes/1/<stamp>.json` (receipt and manifest row, as every Record file), holding counts and the
   `materiality_version`, `materiality_sha256`, `companies_version`, `companies_sha256` it used, no title, URL, symbol or term. The next pass reads
   the latest earlier note and applies the NP7b rule to both files (an older version stops with the `..._rolled_back` code, the same version with
   other bytes with the `..._damaged` code, a file used before that is now missing stops). The comparison is the one function NP7b wrote, made
   shared rather than copied (DRY); a materiality version of its own gets the two `materiality_*` codes that already exist.
   **The pass note is a new file type**, which is the cost of carrying the rule: the read pass has no other per-run file to record the versions in
   (read files are per article). The first note only records. A pass without `apply` (the probe) writes nothing and so does not move the pin.
5. **Report** (counts only): the order used, articles examined, material found, material read, material skipped (unresolved or unlisted), and
   the existing counts. `material_unresolved` shows when the resolve pass is behind: a material headline whose link has not been resolved yet
   cannot be read.

## Decisions I am making (the judge should overrule what is wrong)
- Two tiers, not a score. Rejected: sorting by weight (the weights are the owner's guesses; a finer order would look more precise than it is).
- The pass note rather than putting the versions into each read file: a read file is facts about one page and write-once; a version of the
  rules that chose it is not a fact about the page.
- Applying the pin to the company list in this pass too, because the same note and function make it nearly free. This is the one place I go
  beyond the orchestrator's text (it asked for materiality); say if it should be dropped.

## Said plainly
- No materiality file exists yet (the terms are the owner's private content), so after NP8 the pass still reads newest first until the owner
  writes one. NP8 makes the file effective; it does not make it exist.
- Nothing in this chain has run against real feeds; the share of material headlines, the unresolved share and the run time of ranking 400
  articles are all unmeasured.
- Tests use invented companies and terms; the privacy line holds (no term, symbol or title in git, a log or a pass note).

## Contract rows planned (docs/RECORD_CONTRACT.md, new section "Material-first reads (NP8)")
The order is newest first when either file is not configured and the line says so; a file that exists but cannot be used stops the pass with
its code and writes nothing; material articles are ranked before others and newest first inside a tier; the ranking never reads more than
`MAX_RECORD_READS` Record files; the pass note holds counts and versions only and is written once; an older or edited file than the last note
stops the pass; a probe (no `apply`) writes no note; and the default behaviour of `NewestFirst` is byte-for-byte what the pass did before.

## Size and order
About 250 lines of code in four small files (`reads/order.py`, `reads/pass_note.py`, a shared pin function moved out of `grouping.py`, the wiring)
plus tests; lane 1, two judges. It depends on NP7b (the shared pin function), so it is built after NP7b merges.
