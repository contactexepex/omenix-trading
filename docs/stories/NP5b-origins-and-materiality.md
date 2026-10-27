# NP5b: origins, promotion and materiality

> **DELETED in DEL1 (28 Oct 2026, owner: "get rid of these 400 unused lines."):** `OriginReader`, `PromotionalFilter` and `ArticleViewer`/`ArticleView` no longer exist; `MaterialTerms` and `resolve/effective_url.py` stay. The text below is the record of what was built; `docs/stories/DEL1-delete-unused-derivation.md` says what stayed.

Lane 1, two judges (it decides what is flagged as agency copy or promotional, and what counts as material; it consumes a
private owner file). Plan: [NP5](NP5-origin-filters-and-tagger.md). Contract rows U1 to U12. **Pure code: no request, no file
written, no Record change, no workflow, no dependency.** Everything is computed when an article is read; no recorded byte changes.

## What it is
- `OriginReader.read(host, provider, authors, title) -> Origin(wire, via)` (`origins/origin.py`): an article is an agency's copy
  when, in this order, its host is the agency's domain, its JSON-LD provider or a byline names the agency whole (any case), or its
  title ENDS with an attribution to it (`(Agency)`, `[Agency]`, `- Agency`, `| Agency`; bounded labels, title cut to 1,000
  characters). A title that only mentions an agency is not a copy of it. Agencies come from the source rules (NP1), not from code.
- `PromotionalFilter.check(...) -> Promotion` (`origins/promotional.py`): flagged when the provider, a byline or the source label
  is a listed promotional name, the host is a listed promotional domain, or a listed marker phrase is in the capped title or the
  cleaned summary. Phrases are compiled with `safe_pattern.compile_safe` (NP5a).
- `MaterialTerms` (`materiality/terms.py`) and `PrivateMaterialityFile` (`materiality/file.py`, folder `materiality`,
  `materiality-vN.json`, same versioned-private-file design as the company list): a headline weighs the sum of the terms it
  matches (each once); it is material when the weight is at least 1 AND the tagger gives exactly one `high`-confidence company.
  A mistake in the file is refused with one fixed code (`MATERIALITY_*` in `codes.py`) and no text; a missing or rolled-back
  version stops the reader, never silently falls back.
- `ArticleViewer.view(article, resolution=None, read=None) -> ArticleView` (`news/view.py`): one pure view over a recorded article,
  its resolution and its read file: effective URL (only from the resolution file or the article's own canonical link, never from
  feed text, a label or a page), tier, listed/unlisted, opinion path, wire, promotion, read outcome.

## Said plainly
- The materiality terms are the owner's private content: no `materiality-v*.json` in the repository, tests use invented terms.
  The terms file does not exist yet; until the owner writes one, nothing is material (evidence: reasoning only).
- Wire detection has no lede check (agentic looked at the first sentence); a story that credits an agency only in its body is
  missed. Reasoning only; measured in NP3c if it matters.
- Title attribution is a heuristic: `Rates hold - Agency` is called a copy even if the outlet wrote it itself and credits the
  agency as a source. For a dashboard flag this is acceptable; it never changes a recorded byte.

## Judge 94 round 1 (judge #1)
- B1 accepted, reproduced: an unresolved wrapper whose feed claims a tier-1 agency domain was listed, tier 1 and an agency copy,
  against NP0 section 3. The host is now empty with no URL (U13); the first test had pinned the bug.
- Merge artifact accepted: my branch carried the old H7 plant; main's entry is taken.

## Judge 95 round 1 (judge #2)
- F1 accepted, reproduced: a term equal to the outlet name made "Acme Motors names new chief - Zztv Profit" material. `MaterialTerms`
  now takes the source and drops a trailing " - Source" with the NP5a `without_outlet` (U14, U15). The raw title still goes to
  `OriginReader` (the suffix is how it finds a title attribution). The promotional filter still reads the full title: a marker
  phrase in an outlet's suffix is a signal about the outlet, left as is (reasoning only).
- F2 and the H7 plant: already in fb94003 (NP5a ab4acd2 merged in; main's H7).
