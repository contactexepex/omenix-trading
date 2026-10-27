# Judge 96: NP6 tiered clustering plan (judge #2, plan only)

**Subject:** `story/NP6-plan` at `30e3f89`, `docs/stories/NP6-tiered-clustering.md` (83 lines, the only file changed against
main). This is a plan document for lane-1 code, so the review is lane 1.

**What I read:**
- the plan;
- `fno/ingestion/news/cluster/` (version 1: `cluster.py`, `title_text.py`, `window.py`);
- the resolution file (`resolve/resolution_file.py`) and the resolver's `accept.py`;
- the news manifest columns (`record/manifest.py`);
- NP5b's `origins/origin.py`.

**Evidence labels:** each point is marked *strong evidence* (read in code), *some evidence* or *reasoning only*.

## Blocking (the plan must change before code)

1. **B1: a generic URL turns "same URL" into a merge of unrelated stories.**
   - *Strong evidence that the input can occur:* `accept()` (`resolve/accept.py`) and `clean_https_link` take any clean
     https link that is not Google's own, with no rule on the path. A decoder answer of an outlet's home page, a section
     page or a consent or AMP landing page is therefore recorded as the article's URL. A publisher feed item can also
     carry a home-page or section link.
   - The plan argues that URL identity is transitive and so cannot chain. That holds only while one URL is one story.
     Under "a URL match joins ANY member", one generic URL in a cluster pulls in every article of the 36 h window with
     that URL, whatever their titles. That is the chaining the anchor rule exists to prevent, and it is written
     write-once into `news/clusters/2/`.
   - **Fix:** define a URL as a story identity only when its normalised form has a non-trivial path (not `""` or `/`)
     or a non-empty query. For anything else, fall back to the title match. Add a contract row with a plant:
     "a bare-host or `/` URL never joins".
   - Also bound the effect and count it:
     - record `url_joins_refused` beside `url_joins`;
     - optionally cap URL joins per cluster and count the overflow.

     Measure on real polls whether the path rule is enough (counts only).
2. **B2 (open question 1): the day-level resolution cutoff does not give the determinism it is for. Do not adopt it.**
   - *Strong evidence:* the manifest row has `date` only (`FIELDS = ("date", "article_id", ...)`), and the resolution
     file deliberately has no time.
   - *Reasoning only, but it follows from the rule itself:*
     - On the live hourly run, every resolution present is dated on or before the window-end day, so the rule changes
       nothing.
     - On a re-run of a closed window, a resolution recorded later on the same day as the window end is still included.
       The re-run still gives other bytes and is still refused.

     So the rule adds code and a new reason a URL is ignored, yet leaves the re-run problem unsolved.
   - **Decision I recommend:** state the guarantee honestly as "the same articles, the same resolution set and the same
     company list give the same bytes".
     - The run uses every resolution present when it runs.
     - A re-run of a closed window that sees a different input is refused and reported, exactly as version 1 already
       does for a late article.
     - Record `resolutions_used` (a count) in the format-2 file, so a refused re-run can be explained.
   - Do **not** change NP2c's format. A time in the resolution file would break its "same answer twice is the same
     bytes" property.
   - If the owner later needs exact re-runs, the right place is a time column in the manifest row, not the file. That is
     a separate lane-1 story.
3. **B3: `companies_version = 0` must not be a silent fallback when a company list exists but cannot be read.**
   - As written, a failed Drive read of the company list produces a format-2 file in which no bar ever moves, under the
     same folder and version as files that did move it.
   - Two files of "version 2" would then follow different rules, and nothing but a field inside the file says so.
     *Reasoning only.*
   - **Fix:**
     - `0` only when the Record holds no company list at all;
     - a list that exists but fails to load or verify stops the run with a fixed code (the existing alert path) and
       writes nothing.

     Add a contract row and a plant.

## Must state in the plan (small, not a round on their own)

4. **The bar-mover must pass the article's `source` to `Tagger.tag`, and say which symbols count.**
   - Without `source`, the NP5a outlet-suffix rule does not run, so two stories from an outlet whose name is a listed
     company would lower the bar. That is judge 92 F2 again.
   - "Tags a symbol" should mean `primary ∪ mentioned` of the title-only tag. State this, and pin it in W1.
5. **Open question 2 (36 h window on URL joins): keep it.** I agree, *reasoning only*.
   - It bounds the damage of B1.
   - It splits a live-blog URL reused over days. Splitting is the fail-safe direction: it under-counts corroboration
     and never invents it.
6. **A deterministic precedence rule is needed.** An article can match cluster X by URL and the anchor of cluster Y by
   title. State that URL comes first, and that a URL belongs to the first cluster that took it (one URL, one cluster).
   Pin it as an invariant in W2. The cluster id is the anchor's hash (`cluster.py:66`), so assignment order already
   decides the ids; the URL rule must not change who the anchor is.
7. **"Verified" is too strong for a wire read from the title.**
   - *Strong evidence:* NP5b's `OriginReader` returns a wire with `via=title` from a title attribution such as
     "- Agency", with no page read (`origin.py:46-48`). Under the plan, that view is a verified group.
   - The count cannot rise from this, because one agency is one origin. But one unread outlet that writes "- Agency" in
     its title clears `no_vetted_origin` and `origins_unverified`.
   - **Fix:** count a wire as verifying only when `via` is domain, provider or byline. A title-only wire is a countable
     origin that is not verified.

## Answers to the other questions

- **A URL match joining ANY member: safe against score chaining** (*reasoning only*).
  - A title match still compares with the anchor only, so an article that joined by URL can never become a bridge for
    a title.
  - It is safe against identity chaining only after B1.
- **Origins out of the cluster file: right.** I agree, *strong evidence*:
  - the count depends on the rule files, the resolutions and the read files, all of which change after a cluster file
    is closed (NP0 section 3);
  - writing it would put a number into the write-once Record that goes stale.

  One addition: the `Corroboration` result should carry the rule-file version and the number of read files it used,
  so a number on the dashboard can be traced.
- **Title-only bar, version folder `2` beside `1`, and the dispatch-only workflow until NP7:** agreed.

## Notes (not blocking)

- The normalisation leaves out http/https, `www.`, a trailing `/` and AMP paths. Each omission can only miss a join
  (fail-safe), never make a wrong one. State this, and count the misses later if they matter.
- The planned "newest company list" changes a re-run's bytes once a new list is published. B2's honest guarantee
  covers this, and `companies_version` in the file explains it.
- Size is fine: 83 lines, under the 500-line limit. Lane 1 for both stories is right.

**Verdict: FAIL** (round 1, `30e3f89`).
- B1, B2 and B3 are plan edits, not redesigns.
- Points 4, 6 and 7 should be written into the same edit.
