# Judge 113: NP11 feed provenance plan (judge #2, plan only, privacy focus)

**Subject:** `story/NP11-plan` at `e050a46`, `docs/stories/NP11-feed-provenance.md` (60 lines, the only file changed
against main).
- Lane 1, a plan with two judges; this is judge #2.
- **Scope: in bounds.** It records which feed found each article (derived and archived write-once) and adds a
  read-only self-measurement, the sibling of NP3c.

## The central question: is a private (key, feed id, scope) day file safe? Yes, with one note

*Strong evidence*, read in code:
- **Feed ids are already public.** The poll log records the feed id. A planned `q-` id is a salted HMAC, so it does not
  name the company.
- **Article keys are already public** in `articles.csv`.
- **The JOIN is new.** Joining a key to the feed that found it would show which opaque query found which article. The
  plan keeps the join in private Drive only. Git gets a receipt and a manifest row with no id, key or pair count.
- **The path is safe.** It holds a date, plus for a supplement `sha8` of the pairs: 32 bits of a hash of private
  content, with no practical way back to the pairs.

**Note (not blocking):** the manifest row's `size` (every Record row has one) roughly shows the number of pairs per day,
that is, articles times feeds per article. The article count per day is already public, so the size adds only an
approximate feeds-per-article overlap. Say it plainly in the plan rather than "NO pair count".

## Blocking

1. **B1: the owner's words are not on record.** It is the same finding as judge 112 B1.
   - The plan cites "Owner (28 Oct 2026, relayed)".
   - No `conversations/2026-10-28.md` exists, and no log on main holds the request.
   - **Fix:** record the owner's words verbatim with the decision, and cite them.
2. **B2: staging cleanup can trash a poll before its provenance is recorded** (*strong evidence*).
   - `staging_cleanup/news_proof.py:50-60` treats a staged news poll as promoted when every one of its articles is held
     in the Record. Provenance is not part of that proof.
   - The day file is written only after the day closes, and a late poll goes to a supplement. A poll whose day file or
     supplement failed to write, or is pending, is therefore "promoted" by today's proof and can be trashed after 7
     days.
   - Its pairs would then be lost for good and uncounted. Nothing would show the gap: the recall report would count
     those articles as "no provenance", the same bucket as articles from before NP11.
   - **Fix:** the plan must make the proof also require that the poll's pairs are in a provenance file of its day, or
     state another rule that cannot lose them silently. Add a row and a plant.
3. **B3: the plan does not state its commit paths** (the same class as judge 105 B1 on NP8).
   - `news-promote.yml` has `EXTRA_MANIFESTS: research/data/manifests/news/wrappers.csv`. The guard loops over a
     space-separated list (`ops/commit_news_record.sh:13`), so `provenance.csv` must be added to it.
   - `RECEIPTS: receipts/raw/news` already covers `receipts/raw/news/provenance`.
   - **Fix:** state the workflow change. It is a lane-1 workflow edit, and without it the provenance manifest is never
     committed and the files go unreceipted in git.

## Must state in the same edit

4. **The source of a day file.**
   - It must be built from ALL staged polls of that day for ALL feeds (`gate.py` `_polls(feed, day)`), not from the
     polls one promotion run happens to see.
   - It includes items whose article was already recorded: a repeated article is exactly the "found by more feeds"
     case.
   - Say what happens when one of that day's polls cannot be read when the day file is written. My suggestion: do not
     write the day file, and retry next run; or write it and let the late pairs go to a supplement. Either is fine if
     it is stated and pinned.
5. **The feed-list `scope` key is optional, so older feed-list versions still parse.** State this, so nobody adds it to
   a strict required key set.

## The other questions asked

- **Day-file determinism:** sound, *strong evidence*. Sorted keys and pairs, the open day skipped, and a re-promotion
  that is a no-op, given point 4.
- **Supplement files:** sound. The pattern is additive, like article revisions; the reader unions every file of a day.
  A supplement must hold only pairs not already in that day's files, so a re-run is a no-op.
- **The `unknown` scope bucket:** right. It is never derived from the id, so a missing label cannot flatter the number.
- **Counts-only measurement with a whitelist test:** right. Copy NP3c's final test, which captures all output including
  CLI stdout, not a blacklist.

**Verdict: FAIL** (round 1, `e050a46`).
- B1 is the log entry.
- B2 is one proof rule with a row.
- B3 is one workflow line.
- Points 4 and 5 go in the same edit.
