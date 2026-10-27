# NP11: feed provenance per article (recall becomes measurable), plan

Owner (28 Oct 2026, relayed): record which feed(s) found each article so "how many tagged articles the broad feeds find alone vs the
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

## Design

1. **Separate additive file; the Article is untouched.** Provenance is NOT an Article field: a later poll by another feed would change
   `fixed_fields` and record a false revision (F-series, NP9 F16 reasoning). It is its own write-once Record:
   `news/provenance/1/<YYYY-MM-DD>.json` (IST day of the poll), one per CLOSED day, holding `{"format":1,"day":..,"pairs":{<article key>: [[<feed id>,<scope>],..]}}`,
   sorted keys and sorted pairs, so the bytes are a pure function of that day's staged polls (deterministic; a re-promotion of the same
   polls gives the same bytes = no-op).
2. **Multi-feed.** The value is the SET of feeds that found the key that day (the same article in a broad and a targeted feed shows
   both). Across days the reader unions the day files.
3. **Late polls.** A poll staged after its day file exists would change the bytes. It is never written over: the new pairs go to
   `news/provenance/1/<day>-<sha8>.json` (sha8 of those pairs), the same additive pattern as article revisions (`news/revisions`).
   The reader unions all files of a day. Nothing is ever rewritten.
4. **Today is not written.** The open day is skipped until it is over (so the common case is exactly one file per day).
5. **Private only.** The file is in private Drive. Git gets only what every Record file gets: a receipt and a manifest row
   (`provenance.csv`: path, SHA-256, size, day; NO feed id, NO key, NO pair count). The path holds a date, never an id.
   Reports, logs, alerts and the CLI print counts only. A new walker test plants a feed id, a scope and an article key and asserts none
   appears in any report/log/manifest/receipt string (as NP3c does today); the commit scan still runs.
6. **Feed scope.** The private feed list gains an optional per-entry `scope`: `broad` or `targeted` (parse refuses any other value).
   `plan-feeds` writes `targeted` for every planned `q-` feed it creates. A hand-listed feed with no `scope` is `unknown`: it is never
   guessed from its id and the measurement reports it in its own bucket (so a missing label cannot flatter a number). Where it lives:
   the private feed list in Drive (`feeds/feeds-v<N>.json`), the same place as the salt; nothing public changes. Feed list SHA changes
   only when the owner adds a version.
7. **Measurement (read-only, counts only).** Sibling of NP3c: `news provenance-recall` (own workflow, `contents: read`). For a window
   it reads the day files and the articles, tags each article's title with the existing Tagger, and prints only counts: tagged articles
   in the window, found by broad only, by targeted only, by both, by unknown only, and with no provenance (promoted before NP11).
   No feed id, key, company or symbol in any output; a whitelist test over all output lines, like `compare-clusterings`.
8. **Limit said plainly (strong):** articles recorded before NP11 have no provenance (the Record is empty today, so none yet); and a
   broad feed that returns an item the targeted query also returns is counted "both", which proves overlap, not which feed would have
   been missed (a recall number is only as good as the targeted queries chosen, reasoning only).

## Rows and plants (RECORD_CONTRACT, new section "Feed provenance (NP11)")

P1 the Article's fixed fields never hold a feed · P2 day file bytes deterministic and sorted · P3 a multi-feed article lists every feed ·
P4 the open day is not written · P5 a late poll goes to a supplement file, the day file is never rewritten · P6 no id/key/pair count in the
manifest row or receipt · P7 scope accepts only broad/targeted/absent; absent is `unknown`, never derived from the id · P8 plan-feeds writes
`targeted` · P9 report/log/CLI strings never carry a feed id, scope or key (walker over a planted run) · P10 the recall report is counts
only (whitelist) · P11 the recall buckets are exact (broad only / targeted only / both / unknown / none).

## Open (owner's)

1. Whether hand-listed feeds should be required to carry a scope (stricter than "unknown").
2. The window of the recall report (proposal: last 14 days).
3. Day-file size grows with articles x feeds; fine at expected volumes (reasoning only, unmeasured).
