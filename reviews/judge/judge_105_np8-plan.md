# Judge 105: NP8 material-first reads (plan doc), round 1 at d9f227b: FAIL (two text items)

**Lane 1 plan, sole judge (judge #1).** Branch `story/NP8-plan`, frozen SHA d9f227b: one file, `docs/stories/NP8-material-first-reads.md` (67 lines). I checked the plan's claims against `main`.

## Claims checked (strong evidence, code)
- **Today's read pass picks pages newest first.** `reads/run.py` `_candidates` sorts newest first, stops at `PAGES = 80`, and counts at most `MAX_RECORD_READS = 400` examined articles (`reads/limits.py`).
- **Nothing in `reads/` uses the ranking code.** Neither `Tagger` nor `MaterialTerms` is imported there.
- **"Material" is as described.** `MaterialTerms.is_material` is `weight >= MATERIAL_AT and tag.confidence == HIGH`. The tagger gives `HIGH` only when exactly one symbol is named (`tagger.py:75`). So "material, high-confidence, single-company" matches the code.
- **The codes exist.** `materiality_missing`, `_invalid`, `_rolled_back` and `_damaged` are already in `news/codes.py`.
- **Runs do not overlap.** `news-read-pages` shares the `news-record` concurrency group with promote, cluster and resolve, so two pass notes cannot race on the same stamp.

**Scope (the owner's ingestion-only rule, 27 Oct 2026, as relayed by the orchestrator): in scope (some evidence).** NP8 decides which pages this repository fetches. That is fetch prioritisation, not presentation. It writes nothing a consumer is meant to read as a view.

## B1 (required, text): the new Record file must be wired into the workflow's receipts and commit
- The plan says the pass note gets "receipt and manifest row, as every Record file". But on `main`, `news-read-pages.yml` commits only these paths:
  - `MANIFEST: research/data/manifests/news/reads.csv`;
  - `RECEIPTS: receipts/raw/news/reads receipts/_batches`.
- A pass note written under `news/read-passes/1/` would get its receipt somewhere the workflow does not commit. That is exactly the "Record file with no receipt" judge 62 F-a warns about. Nothing runs the `--unreceipted` check yet, so it would pass silently.
- **Fix, in the plan:**
  - name the note's manifest (or say it shares `reads.csv`, and how its rows differ) and its receipt folder;
  - list the workflow change (`EXTRA_MANIFESTS` and `RECEIPTS`) as part of the story, in lane 1;
  - add a contract row: "the note's receipt and manifest row are committed by the workflow";
  - say whether `staging-cleanup` needs to know the new folder.

## B2 (required, text): the read cap is defined two ways
- Item 2 reads the **article file** of up to 400 newest unread articles to rank them. It then reads a **resolution file** for each Google News item down the ranking.
- The planned contract row says "the ranking never reads more than `MAX_RECORD_READS` Record files". Those two statements conflict: 400 article reads plus the resolution reads is more than 400.
- Today, `examined` counts one Record read per article: the resolution file for a wrapper, the article file otherwise. NP8 roughly doubles the reads for wrappers.
- **Fix:** say which it is.
  - If the cap is **400 articles ranked**, Record reads can reach about 400 + 80 or more.
  - If it is **400 Record reads in total**, the ranking slice shrinks to about 300 articles.
  
  Write that number into the row and the report counts.

## Recommended (an owner decision; reasoning only)
- **A broken materiality file halts all reading, not only the ranking.**
  - A stop is the right default for a write-once pin. But news pages go stale or behind paywalls within days, so while the file stays broken, every pass reads nothing.
  - The alternative to put to the owner: read newest first, go red with the code, and write no note, so the pin does not move.
  - The same stance as NP7b is defensible. Ask the owner rather than decide it here.
- **Pinning the company list in the note as well: accept it.** The same function and the same note make it cheap. Note that the cluster run and the read pass would then pin the list independently, which is fine.
- **The slice limit is stated honestly.** It is about the last six hours at 1,500 articles a day. That figure is agentic's count, not ours, so it is strong evidence only for agentic's feeds. Reporting `material_found` per pass makes the slice measurable later.

## What holds
- A `ReadOrder` strategy with `NewestFirst` byte-for-byte unchanged is a true interface with two uses.
- The pin function is shared from NP7b, not copied.
- Not configured means fall back to newest first and say so; broken or used-and-gone means stop. This mirrors NP7b's rule.
- A probe writes no note.
- Privacy: the note holds counts and versions only.

## Hard lines
No Groww, no orders, and no term, title, URL or symbol in git, a log or the note.

## Verdict: FAIL round 1 at d9f227b. B1 (wire the note's receipt and manifest into the workflow) and B2 (one definition of the read cap) required, both text-only. The halt-versus-fallback choice goes to the owner.
