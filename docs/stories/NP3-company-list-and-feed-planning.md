# NP3: the injected company list and the feed plan (PLAN)

PLAN for the orchestrator's check before any code. Lane 1, **two judges** (it writes the private feed list that decides what omenix
requests, and touches the privacy rule). Plan: [NP0](NP0-news-port-plan.md) sections 2a and 4, **amended here by the owner's direction of
27 Oct 2026** (relayed by the orchestrator): the company list and all fetching are driven by a configurable, injected source; nothing
about the number of companies is in code; discovery is broad and every item is tagged against a name dictionary, NOT 500 per-company
queries. NP5 (the tagger) consumes the same source. Not built; nothing requested.

## The design

**1. `CompanyListSource` (interface) and `Company`.** `companies() -> CompanyList` (a version number plus a tuple of `Company`). A
`Company` is: `symbol` (the NSE symbol), `name`, `aliases`, `exclusions` (regular expressions removed from a text before matching, as
agentic's `news_exclude`), `targeted` (true for names that also get their own search). Nothing else; the count is whatever the source
returns (20, 200, 500). Every consumer (the feed planner here, the tagger in NP5, later NSE company data and financials) takes a
`CompanyListSource` in its constructor and never imports an adapter. Swapping the file for a database or an API is **one new class and
one line in the composition root**.

**2. The first adapter, `PrivateCompanyFile`.** Reads `config/companies-vN.json` in the private Drive config area, with exactly the
discipline of `feeds-vN.json` (P2): the newest version is used, a version older than one already used is refused, a version edited in
place is skipped loudly, errors are fixed codes and never the text. Bad entries are refused (a name that is empty once normalised, a
duplicate symbol, an exclusion that is not a regular expression, a symbol that is not an NSE-style symbol). The file is **content the
owner edits**; nothing in code names a company.

**3. The seed.** A command `news seed-companies` writes `companies-v1.json` from the NSE F&O master already archived in Drive
(`fo_mktlots`: its `UNDERLYING` column holds the company name, its `SYMBOL` the symbol; strong evidence from `fo_masters.py`, I have not
opened a real file here) plus a starter set of aliases and exclusions copied from agentic's 20 companies (HDFC Bank, Mahindra & Mahindra
with its seven exclusion patterns, and so on). The file is marked as a seed: **names are cleaned from the master mechanically ("Ltd",
"Limited" removed) and will be wrong for some; the aliases for the other ~180 names are the owner's content to improve.** `targeted`
starts true for no one; the owner chooses.

**4. Feed planning, not new fetching.** `FeedPlanner` is a pure function: (`CompanyList`, a private `discovery-vN.json`) to a feed list.
`discovery-vN.json` holds the service's search address and parameters, the **broad queries** (indices, themes, sectors, macro; agentic
has 20 such category queries and 6 outlet feeds, the starting point), the template for a targeted query, and the manual publisher
feeds. `news plan-feeds` writes the result as the next `feeds-vN.json` (same salt, the existing write-once rule). So **the fetcher,
Staging, the gate and the poll log do not change at all**: they read a feed list as today. A new company list changes the plan at the
next `plan-feeds`, not the code. **Feed ids are stable, derived from content, and never reused (judge 77 F1).** The gate's `kinds_ever_listed` raises
`FEED_KIND_CHANGED` when one id has two kinds across versions, which stops promotion and the staging cleanup, and staged polls live
under `<feed id>/`. So a planned feed's id is `q-` plus 8 hex characters of the SHA-256 of its kind and its normalised query: the
same query always has the same id, however the list is reordered or extended, and a different query can never take it. The
binding lives in the id itself (no table to lose). The planner refuses a version in which two different queries hash to one id, or
in which an id already used with another kind appears (the two checks that make a re-plan safe), and a test re-plans the same list in
another order and with extra companies and asserts every surviving id is unchanged. Manual publisher feeds keep their `feed-NN` ids.
This needs the id pattern widened to accept `q-<8 hex>` (a P2 change, listed below); the old 999-id lifetime cap goes away.
Three small changes to P2 code in all, each behaviour-preserving for the feeds that exist, each with a test: (1) `MAX_FEEDS` raised
(a config constant; the test that pins the old limit is updated); (2) the feed id pattern accepts the planned form;
(3) `news/session.py`: `NewsSession` is given the per-run pacer built from the feed list instead of the module's `NEWS_PACER`
(`NEWS_PACER` stays as the default for any other caller).

**5. Pacing, with no change to the live pacer.** I first thought this needed a register-host API on `nse_pacer.py` (the orchestrator
flagged it as a shared live file). It does not: `NsePacer(spacing={...})` already takes a per-host spacing table, and unknown hosts get
1.0 s. The composition root builds the news session's pacer from the feed list: `NsePacer(spacing={host: 1.5 for each wrapper feed
host})`. **`fno/shared/nse_pacer.py` is not touched**, the NSE limiter's behaviour cannot change, and no host name is written in code
(the host comes from the private list). A test pins that the NSE table is unchanged.

**5b. Privacy test (judge 77 F2).** `companies-vN.json` and `discovery-vN.json` are written only to the private Drive config area. The
record scan does not catch a list of names, so a test walks the repository and fails if any file named `companies-v*.json` or
`discovery-v*.json` exists in it (built in NP3a, `test_no_company_or_discovery_list_is_ever_in_the_repository`); fixtures in tests use
invented names only, and the seed command's printed line is counts and a code, never a symbol or a name (tested with marker names).

**6. Load.** One request per planned feed per run, 1.5 s apart for the search service: 100 feeds take about 2.5 minutes, 200 about 5.
**Staging volume against the cleanup (judge 77 F4).** Up to one staged poll per planned feed per run: 200 feeds hourly is up to 4,800
staged polls a day (Google's answers change constantly, so I assume few are `unchanged`), against the staging cleanup's `--limit 500`
per run (it examines the oldest first, trashes only polls strictly older than 7 days whose articles are all in the Record). At 4,800 a
day the cleanup falls behind at the default limit. Proposed: run the cleanup daily with `--limit 6000` (the report-only run first
reports the real count) or a few times a day at 2,000; the cost is Drive reads, about one per examined poll. Not decided here; the
staging cleanup workflow's `limit` input already exists, so it is a value, not code.

The service answers at most 100 items per query (agentic measured 7 Oct), so a query that returns 100 over a long window is a signal
of loss, counted in the run line (as agentic's `google_skipped`), not hidden.

**7. The tagger's dictionary (NP5, so the contract is settled now).** `NameDictionary(CompanyListSource)` compiles, per company, the
whole-word patterns of its name and aliases (case-insensitive), the symbol in parentheses (case-sensitive), and its exclusions removed
first; the title decides, the summary only when the title names none (agentic's rule); the result (`primary`, `mentioned`, `confidence`)
is computed on read and never written into the Record (NP0 section 3).

## What I cannot promise (said plainly)
- **Recall is the open risk (reasoning only).** Broad queries return what the search service ranks for a theme; a story about one
  mid-cap among 500 appears only if a broad query, an outlet feed or a targeted query catches it. The tagger finds names in what was
  fetched; it cannot find what was never fetched. Agentic queried each of its 20 names; no one has measured what a broad-only plan loses.
  Proposed measurement, before the owner relies on the news: for one week run the broad plan and a per-company plan for a sample of
  30 names side by side (dispatch-only, counts only) and report the share of per-company items the broad plan also found.
- Name quality: ambiguous names ("ITC", "Titan", "Page") will tag wrong text; the owner's `exclusions` and a symbol-only flag are the
  tools, and the first real week will show the cases.
- The seed's company names come from a file I have not read here.

## Stories this splits into
| # | Story | Contents | Lines (est.) |
|---|---|---|---|
| NP3a | Company list | `CompanyListSource`, `Company`, `PrivateCompanyFile`, `news seed-companies`, versioned-file discipline (reuse by extracting what `feeds.py` does into one helper, with the feed tests as the safety net) | ~350 |
| NP3b | Feed plan | `discovery-vN.json`, `FeedPlanner`, `news plan-feeds`, the raised caps, the per-run pacer from the feed list | ~350 |
| NP3c | Recall measurement | the side-by-side counts-only run | ~150 |

## Needs from the owner
The first real content: which names are `targeted`, better aliases and exclusions than the mechanical ones, and the broad queries
beyond agentic's starter set. None blocks the code; the seed lets it run.
