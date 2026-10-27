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
2. **How the pass uses it, and ONE definition of the read cap (judge 105 B2).** `MAX_RECORD_READS` stays what it means today: **at most 400
   Record files are read in a pass, in total**. Ranking needs each candidate's title and source, so the 400 are split by two new constants in
   `reads/limits.py`: `SCORE_READS = 300` article files (the newest unread articles, ranked) and `RESOLVE_READS = 100` resolution files (a Google
   News item needs one to find its page; read down the ranking until 80 pages are found or the 100 are spent; the unlisted and unresolved ones are
   counted and skipped). Publisher items need no second read. **Consequence, stated plainly: the ranking is applied inside the newest ~300
   articles, not over the 3-day look-back.** At about 1,500 articles a day (agentic's count, strong evidence for its own feeds) that is roughly
   the last five hours, so a material headline is read only if a pass runs within about that time after it was recorded. The report carries
   `scored` and the Record files read, so the real figures show. Raising the split costs Drive reads and run time, both unmeasured; the plan does
   not change the total.
3. **What the pass does with each file (orchestrator's rules; judge 105's recommendation).**
   - **No file configured** (`materiality_missing` or `company_list_missing`): `NewestFirst` (degraded but working), said in the line
     (`order newest_first`). Without a list nothing can be tagged, so nothing could be material anyway.
   - **The MATERIALITY file exists but cannot be used** (invalid, rolled back, edited in place, damaged, store unreadable): **degrade and alert.**
     The pass reads newest first, the run goes RED with the alert (loud, never silent), and **no pass note is written, so the pin does not move.** Reads
     continue, because the materiality file only affects the ORDER of reads: it changes neither what is archived nor how an article is tagged, so a
     broken ordering hint must not halt collection.
   - **The COMPANY LIST exists but cannot be used:** here I **propose the same degrade-and-alert** as for materiality, and I flag that it goes beyond the
     orchestrator's text. Reason: in the read pass the list also only orders the reads (the tag decides which articles are ranked first, and nothing is
     archived from it), so the argument that spares collection applies equally. The hard stop for a bad company list stays where tagging is archived: the
     version 2 cluster run (NP7b, `company_list_rolled_back` / `company_list_damaged`). If the judge or the orchestrator wants the read pass to hard-stop
     on the list, it is one line and one test.
   - A pass that wrote no note because a file was unusable leaves the next pass comparing with the last good note, so a rollback cannot hide behind a
     red run.
4. **The SHA and rollback rule is carried here** (the materiality file is first read in this story): a pass that writes (`apply`) also writes a
   small **write-once pass note** `news/read-passes/1/<stamp>.json` (receipt and manifest row, as every Record file), holding counts and the
   `materiality_version`, `materiality_sha256`, `companies_version`, `companies_sha256` it used, no title, URL, symbol or term. The next pass reads
   the latest earlier note and applies the NP7b rule to both files (an older version is a `..._rolled_back` and the same version with
   other bytes a `..._damaged`; a file used before that is now missing counts as unusable; each is handled by rule 3 above: newest first, red, alert, no
   note, reads go on). The comparison is the one function NP7b wrote, made
   shared rather than copied (DRY); a materiality version of its own gets the two `materiality_*` codes that already exist.
   **The pass note is a new file type**, which is the cost of carrying the rule: the read pass has no other per-run file to record the versions in
   (read files are per article). The first note only records. A pass without `apply` (the probe) writes nothing and so does not move the pin.
   **Its manifest, receipt folder and commit (judge 105 B1).** The note has its own manifest `research/data/manifests/news/read-passes.csv` and
   receipt folder `receipts/raw/news/read-passes`, written through the same `WriteOnceWriter` as every other Record file. `news-read-pages.yml`
   today commits only `reads.csv`, `receipts/raw/news/reads` and `receipts/_batches`, so a note would go unreceipted: NP8 changes the workflow
   (lane 1) to add `EXTRA_MANIFESTS: research/data/manifests/news/read-passes.csv` (the guard already loops over it) and the new receipt folder
   in `RECEIPTS`. Staging cleanup does not need to know the folder: nothing under `fno/ingestion/staging_cleanup` mentions the reads folders
   (checked by search), it proves staged polls were promoted and the note is not one. The `--unreceipted raw/news` check of the cutover gates
   covers the new folder because it walks the whole `raw/news` prefix.
5. **Report** (counts only): the order used, articles examined, material found, material read, material skipped (unresolved or unlisted), and
   the existing counts. `material_unresolved` shows when the resolve pass is behind: a material headline whose link has not been resolved yet
   cannot be read.

## Owner FYI (the orchestrator is putting it to the owner with this as the default)
A broken materiality file degrades to newest first with a red run and an alert; reading is not halted. If the owner prefers a hard stop it is one
line and one test. Reasoning only: the degrade loses no data and is as loud.

## Decisions I am making (the judge should overrule what is wrong)
- Two tiers, not a score. Rejected: sorting by weight (the weights are the owner's guesses; a finer order would look more precise than it is).
- The pass note rather than putting the versions into each read file: a read file is facts about one page and write-once; a version of the
  rules that chose it is not a fact about the page.
- Applying the pin to the company list in this pass too, because the same note and function make it nearly free. This is the one place I go
  beyond the orchestrator's text (it asked for materiality); say if it should be dropped.

## Said plainly
- No materiality file exists yet (the terms are the owner's private content), so after NP8 the pass still reads newest first until the owner
  writes one. NP8 makes the file effective; it does not make it exist.
- Nothing in this chain has run against real feeds; the share of material headlines, the unresolved share and the run time of ranking 300
  articles are all unmeasured.
- Tests use invented companies and terms; the privacy line holds (no term, symbol or title in git, a log or a pass note).

## Contract rows planned (docs/RECORD_CONTRACT.md, new section "Material-first reads (NP8)")
The order is newest first when either file is not configured and the line says so; a materiality file (and, as proposed, the company list) that exists but cannot be used makes the pass read newest first, go red with the alert and write no pass note; material articles are ranked before others and newest first inside a tier; the pass never reads more than
`MAX_RECORD_READS` (400) Record files in total, split 300 article reads for ranking and 100 resolution reads; the pass note has its manifest and receipt folder, the workflow commits them and `scored` is reported; the pass note holds counts and versions only and is written once; an older or edited file than the last note
is treated as unusable (rule 3), never as a reason to stop reading; a probe (no `apply`) writes no note; and the default behaviour of `NewestFirst` is byte-for-byte what the pass did before.

## Size and order
About 250 lines of code in four small files (`reads/order.py`, `reads/pass_note.py`, a shared pin function moved out of `grouping.py`, the wiring)
plus tests; lane 1, two judges. It depends on NP7b (the shared pin function), so it is built after NP7b merges.
