# NP6b: independent origins and flags (the corroboration read-model)

> **DELETED in DEL1 (28 Oct 2026, owner: "get rid of these 400 unused lines."):** `corroborate` and its flags no longer exist (corroboration is derived downstream). The text below is the record of what was built; `docs/stories/DEL1-delete-unused-derivation.md` says what stayed.

Lane 1, two judges. Plan: [NP6](NP6-tiered-clustering.md) (passed by judge 96, round 2). Contract rows W7 to W11b. **Pure code: no request,
no file written, no Record change, no workflow, no dependency.** The count is computed when a cluster is READ from its members' views
(NP5b), never stored, so editing a rule file never leaves a stale number in the write-once Record.

## What it is
- `corroborate(views, rules_version="") -> Corroboration` (`corroboration/origins.py`). Origin label: `wire:<agency>` if the view has an
  agency, else `outlet:<outlet key>`. Views with one label are one origin group (an agency's copies at different outlets, or several
  articles of one outlet).
- A view is *countable* when its outlet is listed and it is not promotional and not opinion. A group is countable if any view is. A
  group is *verified* when a countable view's page was read (`full`, `partial` or `paywalled`) or its agency was proved by the domain, the
  provider or a byline; **an agency named only by the title does not verify** (judge 96 item 7). `independent_origins` = verified groups;
  `unverified_origins` = countable groups that are not.
- Flags (`corroboration/flags.py`, fixed order, each one rule): `promotional_provider`, `single_source` (exactly 1), `no_vetted_origin` (0),
  `origins_unverified`, `opinion`, `low_tier_only` (no listed outlet), `unread` (no page read).
- `Corroboration` also holds `reads_used` and `rules_version`. The source rules have no version number of their own, so the caller says
  what the rules were (a digest of the file is the natural value; NP7 decides). Empty by default.
- `ArticleView` (NP5b) gains `outlet` and `wire_via`.

## Said plainly
- No copy test across outlets (agentic's MinHash is not ported): two outlets that copy a non-agency story count as two origins, so
  `independent_origins` can be too high. Reasoning only; a number is only as good as its `origins_unverified` flag and read count, which travel with it.
- Unlisted articles with no host share the label `outlet:` (empty key): they never count, so this changes no number, but the group is not
  meaningful and must not be read as an outlet.
- Stricter than agentic on one point (**mine**): a title attribution alone does not verify.
- Not ported: `sources_say`, `duplicates_removed`, and the verification-status layer (not read).
