# Judge 77: NP3 company list and feed plan (plan document, lane 1)

Frozen SHA `eb05a7b` (branch `story/NP3-company-list-and-feed-planning`). The branch adds one file,
`docs/stories/NP3-company-list-and-feed-planning.md` (73 lines). The deleted judge_75 seen in `git diff origin/main`
comes only from an older base. Text only, so the gates are the record scan and `check_numbers`.

## (1) The claims about omenix code: correct

| Claim | Where it is in the code |
|---|---|
| `MAX_FEEDS = 50` | `feeds.py:23` |
| The feed id pattern is `^feed-\d{2,3}$` | `feeds.py:22` (so ids stop at `feed-999`) |
| `NsePacer` takes `spacing` | `nse_pacer.py:54`, used at `:62` |
| An unknown host gets `DEFAULT_SPACING_SECONDS = 1.0` | `nse_pacer.py:29`, used at `:140` |
| `NEWS_PACER = NsePacer()` | `news/session.py:16` |
| The gate's and the cleanup's kinds come from `kinds_ever_listed` | `feeds.py:108`, called at `record/wiring.py:30` and `staging_cleanup/wiring.py:92` |
| The `fo_mktlots` key columns are `UNDERLYING` and `SYMBOL` | `research_data/fo_masters.py:17` |

The load arithmetic is right: 100 feeds x 1.5 s is 2.5 minutes, and 200 x 1.5 s is 5 minutes. `news-fetch.yml` has a
30-minute timeout.

**"The same salt" is safe.** The salt only salts the list hash that is logged (`snapshot_log.py:4-5`), so reusing it
across versions reveals nothing while the file stays private.

## (3) Honesty: correct

- The recall risk of broad-only discovery is marked "reasoning only", and it comes with a measurement (NP3c, a week
  side by side on 30 names).
- The seed's names are marked as from a file the builder has not opened.
- Ambiguous names are called out.

## Findings

1. **F1 (must fix): the plan says nothing about how feed ids are assigned, and the existing code makes that a hard
   rule.**
   - `kinds_ever_listed` raises `FEED_KIND_CHANGED` when one feed id has two kinds across any versions
     (`feeds.py:120-121`). That error stops the news promote and the staging cleanup.
   - Staged polls live under `<feed id>/<Y>/<m>/<d>/poll/`, so one id that names two different queries over time
     mixes their histories.
   - A generated plan that numbers feeds by position (`feed-001`, `feed-002` and so on) breaks both as soon as the
     company list or the broad queries change.
   - The plan must state the rule: a feed id is bound for good to one query and its kind, it is never reused, and a
     retired query keeps its id, unused. It must also say where that binding lives, for example in `discovery-vN.json`,
     or derived from the previous feed lists, and add a test that a re-plan keeps every surviving feed's id and kind.
   - With ids never reused, the `\d{2,3}` pattern is also a lifetime limit of 999 ids, not 999 at a time. Say that.
2. **F2 (must fix): the privacy test you asked about is not in the plan.**
   - Item 2 of the request asks for a stated test or scan proving `companies-vN.json` and `discovery-vN.json` never
     enter the repository. The plan says only that they live in the private Drive config area (sections 2 and 4).
   - The record scan looks for credential-like values; a list of company names or search queries passes it.
   - Name the guard. For example, a test that fails if any file matching `companies-v*.json` or `discovery-v*.json` is
     tracked, plus the existing `test_privacy` extended so that no search query or company name list sits in `fno/`
     or `tests/` fixtures beyond made-up names.
3. **F3 (should fix): "two small changes to P2 code" undercounts.** Building the news pacer from the feed list replaces
   the module-level `NEWS_PACER = NsePacer()` (`news/session.py:16`) and its use at `:39`. That is a third P2 change;
   list it. The claim that `nse_pacer.py` itself is untouched holds.
4. **F4 (should fix): the load section leaves out what a bigger plan does to Staging.** 200 feeds means up to 200 staged
   polls per run. The S1 cleanup examines at most `DEFAULT_LIMIT = 500` copies a run (`staging_cleanup/cleanup.py:22`),
   and news-fetch has no schedule yet. State the expected polls a day against the cleanup cadence, so the backlog is
   a number and not a surprise (reasoning only on volume).

**Verdict: FAIL** (round 1, `eb05a7b`). F1 and F2 are missing design rules, not wrong ones; both are a paragraph each.

## Addendum 1: round 2 (final) on `8459517`, the plan document only

I judged only `docs/stories/NP3-company-list-and-feed-planning.md`, as asked (NP3a's code at `91ae2a4` comes
separately). `git diff eb05a7b 8459517` on that file:

| Round-1 finding | Now |
|---|---|
| **F1 (feed ids)** | Fixed as a rule: content-derived `q-` plus 8 hex, never positional, never reused, re-plan test, wider pattern. |
| **F2 (privacy guard)** | Fixed: `test_no_company_or_discovery_list_is_ever_in_the_repository` exists at that SHA (`tests/ingestion/news/companies/test_seed_and_cli.py:148`), plus marker-name tests. |
| **F3 (session.py change)** | Fixed: listed as the third P2 change. |
| **F4 (staging volume)** | Fixed: 4,800 polls a day against `--limit 500`, with a proposal. |

## F5 (must fix, new, introduced by the F1 fix): the unsalted id reveals the owner's queries in the public repository

- The plan's id is `q-` plus 8 hex of SHA-256(kind + normalised query), with no secret in it.
- Feed ids are public. The committed poll log `research/data/manifests/news/polls.csv` has a `feed_id` column, one row
  per poll (`snapshot_log.py:15`, `fetcher.py:80`), and P2 calls that id "opaque".
- So anyone can hash a guess, for example "HDFC Bank" with the targeted-query template, and confirm from the
  repository which companies and themes the owner follows.
- That defeats the rule this plan and NP1 rely on ("what the owner reads stays private"). It is the very attack the
  feed list's salt exists to stop (`snapshot_log.py:4-5`).

Fix in the plan: derive the id from a keyed hash, `q-` plus 8 hex of HMAC-SHA256(salt, kind + normalised query), with
the feed list's own private salt. The plan already keeps "the same salt" across versions, so ids stay stable. State that
the salt and the normalisation function are then frozen (changing either renames every planned feed), and add a test
that the id cannot be reproduced without the salt. Strong evidence on the leak (code read); reasoning only on how much
a 32-bit prefix plus guessable queries reveals. Short queries such as company names are cheap to enumerate.

**Verdict: FAIL** (round 2, `8459517`). F1 to F4 are fixed. F5 is a privacy hole that the F1 rule opens, with a
one-line design fix. This was the second round, so per the round rule the orchestrator or the owner decides next.
