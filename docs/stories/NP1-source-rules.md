# NP1: the news source rules (BUILT, awaiting two judges)

Lane 1, **two judges** (it decides which outlets omenix will ever request: an outside-service rule). The plan is
[NP0-news-port-plan.md](NP0-news-port-plan.md) (orchestrator-approved 27 Oct 2026). This story builds only its section 2(c) and the
data of 2(f), 2(g): the allowlist and the pure lookups. Nothing here makes a request, reads a feed or writes to Drive.

## What it adds
- `config/news_sources.yaml`: **public** data, ported from `contactexepex/agentic-stock-prediction` at `f1b9bb6` (112 outlet domains:
  12 primary, 23 tier1, 77 tier2; 11 marked `fetch: false`; 8 news agencies; the promotional vendor lists). Its sections `selection`,
  `material_terms`, `clusters` and `claims` are left for the stories that use them. `newspaper` is removed from the one outlet that
  listed it (NP0 section 2e). What the owner reads (companies, queries) is **not** here; it stays private (NP3).
- `fno/ingestion/news/sources/`: `model.py` (frozen values), `loader.py` (`load_source_rules`, strict validation), `rules.py`
  (`SourceRules`: `lookup`, `tier_of`, `outlet_key`, `may_fetch`, `may_upgrade_to_https`, `is_opinion`, `domain_of_label`,
  `wire_of_name`, `wire_of_domain`, `is_promotional_provider`, `is_promotional_domain`), `labels.py`. Largest file 152 lines.
- Contract rows **O1 to O8** ([RECORD_CONTRACT.md](../RECORD_CONTRACT.md)), each with a plant that was run and failed a test.
- 52 offline tests (`tests/ingestion/news/sources/`).

## Decisions and why
- **A host matches only at a dot boundary, from the right, and only if it is a plain lower-case ASCII name.** `notreuters.com`,
  `reuters.com.evil.example`, a host with a port, credentials, a space, a path or non-ASCII letters, and an address are all
  "unlisted". Agentic's lookup had the dot-boundary rule but no host-shape check; the check is defence in depth (strong evidence it
  matters: `x y.reuters.com` would otherwise be listed).
- **The loader refuses what it does not know** (unknown key at any level, bad tier, an extractor we do not run, `same_as` to nothing or
  to a chain, a name two outlets claim, a bad wire or promotional entry, a pattern that is not a regular expression). Agentic's loader
  accepted anything; a typo there is a silently ignored rule.
- **Unlisted means never requested and never counted.** `may_fetch` is True only for a listed outlet with `fetch` not false.
- **Not ported yet:** wire detection from a byline or text, the promotional text test, material terms, the learned label-to-domain map.
  Those are NP5's pure modules; NP1 holds only their data.

## What is NOT established (said plainly)
- Every `fetch: false` and note was measured from agentic's cloud on 6 Oct 2026, not from GitHub runners. `fetch: false` can only make us
  request less, so it is safe to inherit; **no outlet is made fetchable** until NP4 re-probes from a runner (reasoning only on what the
  re-probe will show).
- The tiers and the label names are agentic's judgement and have not been re-checked against what Google News prints today (some
  evidence only: they matched 1,533 real reads over three weeks there). A label that no outlet claims is simply unlisted.
- The list is broad on purpose (agentic's policy, 6 Oct 2026); half of the material headlines there came from outlets outside it.

## Judges: please try to break
1. A host that should be unlisted but finds an outlet (try encodings, trailing dots, uppercase, IDNA, `@`, `%`, tabs).
2. A mistake in `config/news_sources.yaml` that the loader accepts.
3. Anything that makes `may_fetch` True for a host the file does not list or marks `fetch: false`.
