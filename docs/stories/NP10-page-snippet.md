# NP10: a bounded snippet of the page (E1 flipped to YES), plan

Owner decision E1 = YES (28 Oct 2026, relayed by the orchestrator; logged verbatim in `conversations/2026-10-28.md`: "For point
number three, per article snippet, yes, please do that. We need that extract, because that will help us to have more enriched and
segregated summary and data." and "switch to yes on the article snippet."). "Small", not the whole body, is this plan's own bound
(the earlier principle of a title, a link and a short summary is in the 25 Oct log). Lane 1 (it changes read-file Record content and keeps more text). Plan first: orchestrator + ONE judge; then
code, two judges, full plant runner. Today: `reads/read_file.py` says "no key sentences" (E1 default), `NP4b` repeats it.

## What changes

The read pass stores, in its own field `summary_extract` of the read file, the first sentences of the page's article body,
bounded and deterministic. The feed's own summary stays in the article file; nothing is mixed. Everything else unchanged: no full
body, no HTML, `body_chars` and `body_sha256` stay (they measure the body).

| Choice | Decision | Why (evidence label) |
|---|---|---|
| Source of the body | the JSON-LD `articleBody` the extractor already parses (`extract.facts_of`) | no new parser and no new dependency (strong: code read). The meta fallback has no body today and keeps none: its snippet is "". |
| Extractor library | the locked `selectolax` only; NO trafilatura | the JSON-LD route needs no DOM walk at all (strong). A paragraph walk of `<article>` for pages without `articleBody` is NOT in this story: how many pages carry `articleBody` has never been measured (nothing has run on real feeds), so it is the owner's call after the first real read pass. |
| Cleaning | strip tags, unescape entities, drop control characters, collapse space (reuse `extract.clean` for the control/space rule) | `articleBody` is often HTML or entity text (reasoning only) |
| Sentences | split after `.`, `!`, `?` (or the Devanagari danda) followed by space, EXCEPT when the next non-space character is a digit or a lower-case letter, or the word before the full stop is in a fixed abbreviation list (`Rs. Mr. Mrs. Ms. Dr. Ltd. Co. No. vs. Inc. Sr. Jr. St.`); the first **3** sentences (judge 112 B2: a join of short pieces alone cut "profit of Rs. | 500 crore") | simple, deterministic, no model (strong for determinism; recall of the split unmeasured) |
| Caps | at most **600 characters** in total, cut at a word boundary; never more than 3 sentences | a small fraction of a body (strong: the cap is fixed in code) |
| Paywalled page | snippet "" (the page itself says it is not free; its articleBody is often a teaser) | said plainly: we do not keep text a paywall hides (reasoning only) |
| Determinism | pure function of the page bytes: same page, same snippet, same file bytes | the read file is write-once, a re-read must be a no-op |
| File format | `FORMAT` 1 → 2 with key `summary_extract`; `MAX_BYTES` 4,000 → 6,000 (600 characters of a three-byte script is 1,800 bytes) | the guard stays: a file over the ceiling is refused, so a body still cannot ride along |

Format compatibility: the read Record is empty (no `research/data/manifests/news`, no `receipts/raw/news` in the repo, as for NP9),
so nothing is migrated; `parse_read` accepts format 2 only. If real reads exist by merge time the plan changes to "read 1 and 2".

## Hard lines kept

- **Private only.** The snippet is in the read file in private Drive and nowhere else: never in git, a manifest row, a receipt, a
  run log, a Slack alert or a report. Reports and logs print counts only; a new test walks every report/log string of a pass with a
  planted snippet and asserts the snippet never appears (rows below). The commit scan still runs.
- **Research only; no new fetch, host or request.** The page is the one already fetched; no extra network call.
- **Anti-spoof unchanged.** The snippet is page text, untrusted: it never sets a host, a tag, a tier, a symbol or a cluster. Nothing
  reads it in this repository (consumers read it downstream).
- **Bounded work.** The extractor works on the JSON-LD block already capped at 1,000,000 bytes; the sentence split is linear.

## Rows and plants (to be added to `docs/RECORD_CONTRACT.md`, section "Page reads")

S1 first sentences only and at most 3 · S2 total at most 600 characters, word-boundary cut · S3 a long piece ending in "Rs." before a number stays one sentence, and so does one ending in a listed abbreviation or before a lower-case word · S4 paywalled page gives "" · S5 meta-only page gives "" · S6 same page, same bytes · S7 file over `MAX_BYTES` refused ·
S8 `parse_read` refuses the old format / unknown key · S9 snippet never in a report, log, manifest row or alert · S10 tags and
entities stripped · S11 a `partial` page (a body under 300 characters) gives its whole short body cut by the same caps, a `paywalled` page "" and a meta-only page "". Each with a plant (the cap, the count, the paywall guard, the join, the privacy check).

## Open (owner's, not decided here)

1. Whether to add the paragraph-walk fallback after the first real read pass shows the `articleBody` share.
2. The numbers 3 sentences / 600 characters are my proposal (reasoning only); the owner said "small", not a number.
3. Copyright: storing publisher text, even privately, is the owner's decision; this repository stores it private-only and short.

## Judge 112 conditions (27 Oct 2026)

- **B1 (owner's words on record):** the owner's words, as relayed by the orchestrator, are logged verbatim in
  `conversations/2026-10-28.md` ("For point number three, per article snippet, yes, please do that. We need that extract, because
  that will help us to have more enriched and segregated summary and data." and "switch to yes on the article snippet.") with the
  decision E1 = YES. They reach me through the orchestrator, not typed to me, and the log says so.
- **B2:** the split rule above, with the S3 test.
- **(d)** "No read file exists" is re-checked as a merge-procedure step: the merge is held if `research/data/manifests/news/reads*` or
  `receipts/raw/news/reads*` exist on main.
- **(e)** row S11 says what a `partial` page gives.
