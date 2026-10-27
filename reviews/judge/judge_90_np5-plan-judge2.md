# Judge 90: NP5 tagger, origins and materiality plan (plan document, lane 1), judge #2

Frozen SHA `4a322e9` (branch `story/NP5-plan`; `bc09d58` plus one bullet, which leaves `cluster/entities.py` to NP6).
The branch adds one file, `docs/stories/NP5-origin-filters-and-tagger.md` (69 lines). Text only. I checked its claims
against main.

## Your seven points

1. **The tagger rules:** headline first, the summary as a plain-text fallback, comparisons and lists demoted, and the
   confidence rule. They are clear and testable. Where they come from is stated honestly ("I read the first half"). I
   cannot compare them with agentic's code (no access).
2. **Not porting the broker "actor" heuristics:** acceptable for a first cut. The effect (a broker tagged as primary)
   is stated, and the remedy (exclusions, low confidence, a later `Actor` strategy) is named. Reasoning only.
3. **One shared grammar and a 1,000-character cap:** right in principle, and the cap with a plant is the hard bound I
   asked for (judge 78). **But see F1:** the grammar cannot take the promotional patterns already shipped.
4. **Materiality terms as a private versioned file, with nothing shipped:** correct, the same discipline as the
   company list.
5. **Wire detection from byline, provider, domain and title attribution only:** consistent with the E1 default, and the
   lost recall is stated.
6. **The privacy test:** overstated; see F2.
7. **The NP5a / NP5b split, and `entities.py` left to NP6:** sensible. NP5 changes no recorded byte, and a clusterer
   change belongs with a new cluster-file algorithm version.

## Findings

1. **F1 (must fix): the shared grammar cannot read the promotional patterns already shipped.**
   - The plan says promotional marker phrases are matched "with the bounded pattern grammar" (line 24) and that every
     owner pattern uses the one allow-list (line 32).
   - `config/news_sources.yaml` `promotional.text` holds 8 patterns, accepted today by NP1's loader with only
     `re.compile`. I ran NP3a's `EXCLUSION_GRAMMAR` and caps over them: **2 of 8 fail**, `Target Price \(Mid\)` (escaped
     parentheses) and `Zacks Rank #` (`#`).
   - If NP5 applies the grammar to that public file as planned, loading the source rules fails, and every news reader
     that loads them stops.
   - The plan must say which way it goes: either widen the grammar for escaped `\(` and `\)` and the characters `#`,
     `/`, `:` (still no repeats), or rewrite the two patterns. Either way NP1's loader validates `promotional.text` with
     the same grammar, and a test asserts the shipped file loads.
2. **F2 (must fix): the privacy claim is stronger than any test can deliver, and the plan breaks it itself.**
   - Line 57 promises "nothing in the repository holds a company name or a materiality term (a test walks the
     repository, as NP3a does)".
   - NP3a's walk (`test_seed_and_cli.py:148-153`) checks only **file names** (`companies-v*.json`, `discovery-v*.json`).
     It cannot detect a name inside any file, and no test can, without the private list.
   - The plan itself uses real listed names as examples (line 14: a real symbol in `(… )` and `(NSE: …)`; line 65: two
     real company names).
   - Say what the test really guards (no `materiality-v*.json` file in the repository, alongside NP3a's names; fixtures
     with invented names only). Replace the real-name examples with invented ones, as NP3a's story now does.

## Notes (not blocking)

- The title attribution for wires ("(Reuters)") and the "trailing outlet name removed" cleaning both match at the end of
  a string. With the 1,000-character cap applied to the title too, say whether the cap is taken before or after the
  cleaning, so that an attribution at the end of a long summary is not cut off.
- `MaterialTerms` requires "exactly one company with high confidence". So the owner's list quality decides
  materiality. That is worth a line in the go-live notes.

**Verdict: FAIL** (round 1, `4a322e9`). Both findings are short fixes to the plan.

NP4b at `9a12caf`: the only change since `337f0ea` is `PYTHONUNBUFFERED` in the probe workflow (my NP4a should-fix). My
F1 (`RecursionError`) and F2 (no deadline per fetch) are untouched, so **judge 89's FAIL stands**.
