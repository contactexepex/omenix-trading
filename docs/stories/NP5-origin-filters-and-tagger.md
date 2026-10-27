# NP5: what an article is about and where it came from (PLAN)

PLAN for the orchestrator's check and one judge before any code. Lane 1 for the code that follows (it decides what the dashboard
shows and what counts as an independent origin; it consumes the owner's private company list). Plan: [NP0](NP0-news-port-plan.md)
sections 2f to 2h, with the changes below. **Pure code: no request, no file written, no Record change, no workflow.** Every judgement
here is computed when an article is READ, never stored (NP0 section 3), so editing a rule never changes a recorded byte.

I read the first half of agentic's tagger (`analytics/news_tags.py`: its docstring, the text cleaners, the actor/list/comparison
patterns, `Tagger.classify` signature) and the start of `cluster_origins.py`; I have not read all of either. Where a rule below is
ported I say so; where it is mine I say so.

## What it builds (three small pure parts, one dictionary)
1. **`NameDictionary(CompanyListSource)` and `Tagger` (NP5a).** For each company of the injected list: its name and aliases as
   whole words, case-insensitive, and its symbol in parentheses, case-sensitive (`(TCS)`, `(NSE: TCS)`), after its exclusions are removed
   from the text. **Headline first** (agentic's rule, issue 29): the title is the subject; the summary (plain text: tags, entities, URLs,
   bare domains and the trailing outlet name removed) is used only when the title names no company; a search query that found the item
   never tags it. Output `Tag(primary, mentioned, confidence)`: a company named in the title is primary; several title companies, a
   comparison title ("X vs Y", "versus", "v/s") or a list ("A, B and C rise") make them mentioned; a company found only in the summary is
   mentioned; `high` confidence = exactly one company in the title and it is primary, `low` for any other tagged item, none for none.
2. **`OriginReader` and `PromotionalFilter` (NP5b).** From facts only: the outlet's domain (`source_domain` of the article file, or the read
   file's host), the read file's provider and bylines, and the title; against the public rules already in `config/news_sources.yaml`
   (8 wire agencies with names and domains, the promotional providers and domains). An article whose byline, provider, outlet domain or
   title (a trailing "(Reuters)"-style attribution) names an agency is a copy of that agency's story: one origin however many outlets carry it.
   A promotional provider or domain flags `promotional`. Marker phrases in the text are matched with the bounded pattern grammar below.
3. **`MaterialTerms` (NP5b).** Weighted title terms deciding which articles are worth a page read first. The terms and weights are the
   owner's content: a private `config/materiality-vN.json` read with the same versioned-file discipline as the company list and the
   discovery file (newest wins, rolled-back and damaged are fixed codes, never in the repository). A starting set is a go-live item for
   the owner; none is shipped in code. An item is "material" when its weight is at least 1 and its title names exactly one company with
   high confidence (agentic's selection, ported as a rule, not its numbers).

## Decisions I am making (the judge should overrule what is wrong)
- **One pattern grammar for every owner-supplied pattern.** Exclusions (NP3a), material terms and promotional marker phrases all use
  the same allow-list (plain text, up to two `(?:A|B)` groups, at most four optional letters, one trailing `\\w*`). The code lives in one
  place and is imported, not copied. Cost to the owner: no full regular expressions anywhere (already accepted for exclusions).
- **The hard time bound on tagging is a text cap.** judge 78 measured an allowed pattern taking 25 s on a 3,000-character summary before
  the group cap; the grammar now bounds it by construction, and **every pattern still runs against at most the first 1,000
  characters** of the title or plain-text summary (defence in depth, a plant: a very long summary with the heaviest allowed pattern
  finishes inside a stated bound). Names and aliases are matched as escaped literals, never as the owner's patterns.
- **Not ported in this cut: the "actor" rules** (a bank acting on another company: analyst actions, holdings, venues, `broker: true`).
  They are long, US-broker-specific heuristics and the company list has no `broker` flag. Effect (reasoning only): a headline such as a
  broker's rating action on a company may tag the broker as primary. The owner's exclusions and the `low` confidence of lists and
  comparisons are the tools until the first real week shows how often it happens. Adding an `Actor` strategy later is one new class.
- **Wire detection loses the lede** (NP4 decision, E1 default no key sentences): only byline, provider, outlet domain and a title
  attribution are used. Said so in the story; measured on the first real reads.
- **No new dependency, no network, no clock**: standard library only (`re`, `html`).

## Rows and tests promised
Per claim, a test and a plant: names are whole words (no match inside a longer word); the symbol is case-sensitive and parenthesised;
exclusions remove text before matching; headline first and the summary only as fallback; comparison and list demotion; confidence
rule; plain-text cleaning (a Google summary linking the search host never tags anything); the 1,000-character cap; a wire agency from
each of byline, provider, domain and title attribution; a promotional provider or domain; unlisted outlets never counted as vetted;
material terms need weight and a single high-confidence company; the private materiality file's discipline; nothing in the repository
holds a company name or a materiality term (a test walks the repository, as NP3a does for companies).

| # | Story | Contents | Lines (est.) |
|---|---|---|---|
| NP5a | Tagger | `plain_text`, `NameDictionary`, `Tagger`, `Tag`, the shared pattern grammar extracted from `companies/parse.py`, the 1,000-character cap | ~350 |
| NP5b | Origins and materiality | `OriginReader`, `PromotionalFilter`, `MaterialTerms`, `materiality-vN.json` adapter, the read-model view that joins an article with its resolution and read file | ~400 |

## What I cannot promise (said plainly)
- Name quality: short or common names ("Titan", "Page") will tag wrong text; exclusions and `low` confidence are the tools.
- Recall of the tagger is bounded by the aliases the owner writes: the seed ships only the four index aliases, so the first tags are
  name-only (known go-live step).
- Wire detection without a lede will miss some agency copies; the rate is unmeasured until real reads exist.
- Tier, wire, promotional and material flags are views: if a rule changes, past articles are re-judged on the next read, by design.
