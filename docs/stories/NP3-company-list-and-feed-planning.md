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
next `plan-feeds`, not the code. Two small changes to P2 code: `MAX_FEEDS` (50) and the feed id pattern limit are raised (a config
constant, with the test that pins the old limit updated) because a plan can hold more than 50 feeds.

**5. Pacing, with no change to the live pacer.** I first thought this needed a register-host API on `nse_pacer.py` (the orchestrator
flagged it as a shared live file). It does not: `NsePacer(spacing={...})` already takes a per-host spacing table, and unknown hosts get
1.0 s. The composition root builds the news session's pacer from the feed list: `NsePacer(spacing={host: 1.5 for each wrapper feed
host})`. **`fno/shared/nse_pacer.py` is not touched**, the NSE limiter's behaviour cannot change, and no host name is written in code
(the host comes from the private list). A test pins that the NSE table is unchanged.

**6. Load.** One request per planned feed per run, 1.5 s apart for the search service: 100 feeds take about 2.5 minutes, 200 about 5.
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
