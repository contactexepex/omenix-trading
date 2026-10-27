# NP3a: the injected company list (BUILT, awaiting two judges; stacked on the NP3 plan)

Lane 1, **two judges** (private content, a new Drive write, a shared helper extracted from the live feed code). Plan:
[NP3-company-list-and-feed-planning.md](NP3-company-list-and-feed-planning.md) (orchestrator-approved). Makes no request to a news
service; reads NSE lists from the Drive archive; the one write is `companies/companies-v1.json`, only with `--apply`.

## What it adds
- `news/companies/`: `model.py` (`Company`, `CompanyList`, the `CompanyListSource` interface), `parse.py` (the checks, one fixed code),
  `private_file.py` (`PrivateCompanyFile`, the first adapter), `seed.py` (pure), `cli.py` (`news seed-companies`), `wiring.py` (the
  composition root). The count of companies is the file's content; no consumer imports an adapter.
- `news/versioned.py`: the "newest version, none older than one used, an edited one skipped" logic **extracted from `feeds.py`** into
  `VersionedFiles`; `PrivateFeedLists` now uses it. The 487 feed and news tests passed unchanged (the safety net). The feed list's
  behaviour, codes and tests are untouched.
- Contract rows **Q1 to Q7**, plants run; 52 new tests.

## What I found reading real data (strong evidence; NSE public lists, read from the Drive archive)
- `fo_mktlots` has 221 lines: six index rows, then 212 stocks after a repeated header. Its `UNDERLYING` names are **abbreviated by NSE**
  ("ZZALPHA HOLDINGS ENTER. L", "ZZDELTA CAPITAL FIN LTD"), so the NP3 plan's idea of using them as names was wrong. The seed takes the
  name from the equity list ("Zzalpha Holdings Enterprise Limited"), then the Nifty 500 list, and only last the master (row Q4).
- Built on the real files (26 Oct master, 12 Oct equity and Nifty 500 lists): **503 stocks (the F&O underlyings plus the Nifty 500) and
  6 indices; the whole file passes the checks; no collisions.** Not committed: it is the seed's output, which goes to the private Drive
  only with `--apply`, and a test proves no `companies-v*.json` or `discovery-v*.json` is in the repository.

## Decisions and why
- **The starter aliases of the reference project's 20 are NOT in this code.** They would put the owner's selection in a public repository. The
  seed has aliases only for the four index underlyings (NSE's own public names); everything else is the owner's to add in a new version
  of the file. This lowers the quality of the first tags until the owner edits, and I say so.
- **Exclusions are an allow-list, not a list of refused shapes** (judge 79 B1, judge 78 F1): plain text, `(?:A|B)` alternatives of plain
  text, `x?` optional letters (at most four, at most two groups) and one trailing `\w*`, at most 120 characters, at most 20 per company. A first fix that only
  capped repeats was measured and is not enough (two `.*` took 14 s on 5,000 characters, six on 90 took 18.7 s), because a refused-shape
  list cannot be complete. 23 chained `(a|a)` groups took 20 s on 100 characters (judge 79), which is why groups are capped at two. Even so, the pattern grammar is a guard against mistakes; the HARD bound on tagging time is the NP5 text cap (the tagger cuts the text each pattern sees to a fixed length: bounded text × a bounded pattern = bounded time). The owner loses regex power she never needed for names; if a real need appears, widen the grammar by a story.
- **The seed skips and counts rows the list checks would refuse, and parses its own bytes before returning them** (judge 78 F2), so a
  bad NSE row can never produce a file that is written once and then stops every consumer.
- **No hash or content of the list is ever printed or logged** (unlike the feed list, whose salted hash is in the poll log).
- **A seed is never written over an existing list;** the owner adds `companies-v2.json` by hand or by a later command.

## What is NOT established (said plainly)
- The seed has not been written to the real Drive (a dispatch needs the owner's go; the report-only run is the first step).
- Short all-capital names stay capital ("ZZQ"), longer ones are title-cased (a long all-capital name becomes "Xxxx Yyyy Zzzz"): mechanical, sometimes wrong.
- Ambiguous names ("Titan", "Page Industries") will tag wrong text in NP5; the owner's exclusions are the tool, not code.

## Judges: please try to break
1. A file shape the parser accepts that should be refused (an exclusion that runs for ever, a name that collides after normalising).
2. Anything in `VersionedFiles` that behaves differently from the old `PrivateFeedLists` (compare with `git show main:fno/ingestion/news/feeds.py`).
3. Any path by which a symbol, a company name or a pattern reaches a printed line, a log or a committed file.
