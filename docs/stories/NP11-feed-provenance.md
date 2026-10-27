# NP11: feed provenance per article (recall becomes measurable), plan

Owner decision (28 Oct 2026, relayed by the orchestrator; logged verbatim in `conversations/2026-10-28.md`: "For point number 5, recall measurement, we store a feed ID on each article. I want to add it, so do that."): record which feed(s) found each article so "how many tagged articles the broad feeds find alone vs the
targeted per-company queries" can be answered. Lane 1, privacy-critical: orchestrator + TWO judges on the plan (privacy focus), then
code, two judges, full plant runner. Evidence labels: strong (read in code), some (reasoned from code), reasoning only.

## Facts that shape it (strong, from code at main)

- A feed id is already public: the poll log in git records `feed id, staging path, SHA-256, size` (`news/wiring.py`). A planned feed
  id `q-` + 12 hex is an HMAC-SHA-256 with the list's private salt (`planning/query_id.py`), so it does not reveal the company; a
  listed `feed-NN` id is plain.
- Article keys are public in the manifest (`articles.csv`). So the DANGER is the JOIN "this article key was found by that feed id":
  with it, anyone could see which opaque query found which article. That join must exist only in private Drive.
- Promotion knows the feed while it reads a staged poll (`record/gate.py::_poll(feed)`); the Article does not carry it, and must not
  (`fixed_fields`, see below).
- Today a feed has an item `kind` (`publisher`/`wrapper`) and nothing says broad or targeted.

## Design (round 2: judges 113 and 114)

1. **Separate additive file; the Article is untouched.** Provenance is NOT an Article field: a later poll by another feed would
   change `fixed_fields` and record a false revision (NP9 row F16 reasoning). Its own write-once Record:
   `news/provenance/1/<YYYY-MM-DD>.json` (IST day of the poll), one per CLOSED day:
   `{"format":1,"day":..,"seal":..,"pairs":{<article key>: [[<feed id>,<scope>],..]}}`, sorted keys and pairs, so the bytes are a pure
   function of the day's staged polls and the feed list's salt (a re-promotion of the same polls gives the same bytes = no-op).
2. **Multi-feed.** The value is the SET of feeds that found the key that day; the reader unions day and supplement files.
3. **The seal (judge 114 B1, the privacy fix).** Keys are unsalted digests of public guids and URLs, feed ids are public in the poll
   log, scope has three values: so a file without the seal is a low-entropy function of public data, and its public receipt SHA-256
   could be matched by building candidate files, confirming a key-to-`q-`feed pair and so a tracked company. Every provenance file
   therefore carries `"seal": HMAC-SHA-256(feed-list salt, "provenance" 0x00 <path>)` as a field of the file: the bytes (and so the
   receipt SHA) cannot be rebuilt without the salt, while the file stays deterministic for a given salt (the salt is frozen: planned
   ids depend on it too, `planning/query_id.py`). The receipt and manifest machinery is unchanged. Principle, stated for any future
   file: a file that is a pure function of public values must carry a salted seal before its SHA-256 is published; read and
   resolution files are high-entropy (page text, times) and need none.
4. **Supplements (late polls).** A poll staged after its day file exists puts only the pairs the day's files do not hold yet into
   `news/provenance/1/<day>-<n>.json`, n = 1, 2, ... the next free number (no hash of the pairs in any name; judge 114 B1), sealed with
   n in the HMAC message. Nothing is rewritten. The reader unions all files of a day.
5. **Today is not written.** The open IST day is skipped until it is over.
6. **What git sees.** Receipt and manifest row `provenance.csv` (path, SHA-256, size, day). No feed id, no key, no pair list. **Said
   plainly: the `size` column shows roughly how many pairs a day holds** (judges 113, 114); it reveals a volume, not a pair.
   Reports, logs, alerts and the CLI print counts only (walker test over planted ids/keys/scope/seal).
7. **No silent loss (judges 113 B2, 114 B2).** Staging cleanup (`staging_cleanup/news_proof.py::NewsPollProof.promoted`) trashes a
   promoted poll after 7 days and today knows nothing of provenance. The proof gains one more condition: every `(article key, feed)`
   pair of the poll must be held by the provenance files of the poll's IST day; otherwise the poll stays staged (it is re-read on every
   run, so a later promotion writes the supplement and the poll then becomes removable). The same walk gives the writer a counted
   code, `provenance_polls_missing`, so a day that could not be completed is visible, never silent. Explicit gate, no timing
   assumption. An unreadable poll at write time (rejected items, damaged file, feed not in the list) adds no pairs, is counted in
   `provenance_polls_skipped`, stays staged (the existing proof already refuses it) and so heals on a later run.
8. **Which polls.** The day's pairs come from ALL staged polls of that IST day for ALL feeds in the list (`gate._polls(feed, day)`),
   including articles already recorded earlier; the writer never needs the article to be new.
9. **Feed scope.** Optional per-entry `scope` (`broad` | `targeted`) in the private feed list `feeds/feeds-v<N>.json`; the parser
   refuses any other value; a list with no `scope` still parses (old lists keep working). Reaching real labels needs the owner to add
   a NEW feed-list version (versions are write-once); until then every hand-listed feed is `unknown`. `plan-feeds` writes `targeted`
   for every planned `q-` feed it creates. Default decided by the orchestrator (overridable): a hand-listed feed without scope is
   `unknown`, never derived from its id.
10. **Workflow.** `news-promote.yml` `EXTRA_MANIFESTS` gains `research/data/manifests/news/provenance.csv` (the commit guard loops
    over that list); `RECEIPTS receipts/raw/news` already covers `receipts/raw/news/provenance`. Same pattern as `read-passes.csv`.
11. **Measurement (read-only, counts only).** `news provenance-recall` (own workflow, `contents: read`), window as a CLI parameter,
    default 14 days (orchestrator default). It reads day and supplement files and the articles, tags each article's title with the
    Tagger, and prints only counts: tagged articles in the window; found by broad only / targeted only / both / unknown only / no
    provenance (before NP11). No feed id, key, company or symbol in any output; a whitelist test over all output lines copied from
    NP3c's final whitelist test (`compare` tests).
12. **Limit said plainly (strong):** articles recorded before NP11 have no provenance; "both" proves overlap, not what a feed would
    have missed (a recall number is only as good as the targeted queries chosen, reasoning only).

## Rows and plants (RECORD_CONTRACT, new section "Feed provenance (NP11)")

P1 the Article's fixed fields never hold a feed · P2 day file bytes deterministic and sorted · P2b the seal: without it the file's SHA-256
is reproducible from public data (a test builds the unsealed file and shows the sealed one differs; plant: seal removed) · P3 a multi-feed
article lists every feed · P4 the open day is not written · P5 a late poll goes to a numbered supplement, the day file is never
rewritten, no pair hash in a name · P6 no id/key/pair list in the manifest row or receipt · P7 scope accepts only broad/targeted/absent;
absent is `unknown`, never derived from the id; an old list without scope parses · P8 plan-feeds writes `targeted` · P9 report/log/CLI
strings never carry a feed id, scope, key or seal (walker over a planted run) · P10 the recall report is counts only (whitelist) · P11 the
recall buckets are exact · P12 cleanup keeps a poll whose pairs are not in the provenance files of its day, and removes it once they are
(plant: the pairs check dropped) · P13 `provenance_polls_missing` and `provenance_polls_skipped` are counted · P14 the workflow commits
`provenance.csv` (workflow text test).

## Open (owner's; defaults taken by the orchestrator, overridable)

1. Hand-listed feeds without a scope are `unknown` (not required). 2. The report window is 14 days, a CLI parameter. 3. Day-file size
grows with articles x feeds: unmeasured, fine at expected volume. 4. The owner must add a feed-list version with `scope` labels for
hand-listed feeds before the first real run if they want them in `broad`/`targeted` rather than `unknown`.

## As built (differences from the plan, said plainly)

- **Scope labels (corrects item 9):** `plan-feeds` labels the discovery file's publisher feeds and its broad queries `broad` and each
  company's own query `targeted` (not "every `q-` id targeted": broad queries are `q-` ids too). Row B10. Hand-listed feeds stay
  `unknown` until the owner adds a feed-list version with labels.
- **Counts:** the promote report counts `provenance_poll_skipped` (a poll that could not be read at write time), `provenance_unreadable`
  (a damaged file of the day), `provenance_conflict`, `provenance_failed`. The cleanup side has no separate counter: a poll whose pairs
  are not recorded is simply not "promoted", so it shows in the existing `unproven` count and stays staged. A feed removed from the list
  keeps its staged polls for good and is already counted by `feed_unknown` (judge 114 note 1).
- **Scope is baked in when a file is written** (judge 114 note 2): a label added later does not relabel old files. The recall line shows
  `with_unknown_feed` so the owner sees how much of a number rests on unlabelled feeds.
- Rows are B1-B16 (`B` is the free prefix); the planned P-numbers map as: P1 B1, P2 B2/B3, P3 B4, P4 B5, P5 B6/B6b, P6 B7, P7 B9/B9b,
  P8 B10, P9 B15, P10/P11 B13-B15, P12 B11, P13 B8/B8b, P14 B12.
