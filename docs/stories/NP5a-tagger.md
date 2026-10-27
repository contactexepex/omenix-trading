# NP5a: the tagger

Lane 1, two judges (it decides what the dashboard says an article is about, consumes the owner's private company list, and
changes the shared pattern grammar). Plan: [NP5](NP5-origin-filters-and-tagger.md) (passed by judge 90 after round 2). Contract
rows T1 to T12 (and Q1/Q8/Q12 re-pointed). **Pure code: no request, no file written, no Record change, no workflow, no
dependency.** Every tag is computed when an article is read; editing the company list changes tomorrow's tags, never a
recorded byte.

## What it is
- `NameDictionary(CompanyList)` (`tagging/dictionary.py`): the injected list (`CompanyListSource`, NP3a) as a lookup of whole-word
  names and aliases to symbols, the symbol set, and each company's exclusions compiled with the safe pattern grammar. Rebuilt from
  the source; nothing names a company in code.
- `Tagger` (`tagging/tagger.py`) and `Tag(primary, mentioned, confidence)`. Rules (ported from agentic unless marked mine):
  headline first (title decides, cleaned summary only when the title names nobody, then only as mentioned); a company in the title
  is primary, except in a comparison ("vs", "versus", "v/s") or a list (comma or slash separated), where it is mentioned; **mine: a
  list needs two companies in the title**, so "A, the largest lender, rises" keeps A primary; `high` confidence = exactly one title
  company and primary; `low` for anything else tagged; none for nothing. A name matches only as whole words in any case, the longest
  name at a position wins, a symbol only in brackets and capitals (`(SYM)`, `(SYM:NSE)`, `(NSE: SYM)`), and a hit inside the company's
  own excluded phrase does not count.
- `tagging/text.py`: `plain_text` (tags, entities, URLs, bare domains and the trailing outlet name out; a link or a source name never
  becomes a company), and the cuts: a summary to 20,000 characters before cleaning, **every text any pattern sees to 1,000 characters
  after cleaning** (the hard time bound the pattern grammar leans on, with a plant). The cleaners are linear: the tag pattern never
  reads past the next `<` and the bare-domain pattern has bounded labels (the first version of mine was quadratic on a run of
  `a.a.a.`; the test found it).
- **`news/safe_pattern.py`**: the allow-list grammar, taken out of `companies/parse.py` so that exclusions, the shipped
  promotional phrases and (NP5b) material terms share one definition. **Widened by the literals `# / :` and the escaped `\.`, `\(`,
  `\)`** because 2 of the 8 shipped `promotional.text` phrases did not fit (judge 90 F1); literals add no ambiguity, so the group,
  optional-letter and word-tail bounds are untouched. The source-rule loader now checks `promotional.text` with it, and a test loads
  the shipped file.

## Said plainly
- Not ported: agentic's "actor" rules (a broker acting on another company: analyst actions, holdings, venues). A broker's rating
  action on a company may tag the broker as primary until the owner writes exclusions; adding an `Actor` strategy later is one class.
- Tag quality is bounded by the aliases the owner writes: the seed ships only the four index aliases, so the first tags are name-only.
- A company whose name is an ordinary word will tag wrong text; exclusions and `low` confidence are the tools.
- Tests use invented companies only. What guards privacy is: no `companies-v*.json` file in the repository (a file-name walk), the
  seed's four public index names, the commit hook's record scan, and placeholders in code and docs; a blanket "no company name in the
  repository" cannot be checked mechanically and is not claimed.

## Judge 92 round 1 (judge #2), all three checked with invented names and accepted
- F1: "Zzalpha's profit jumps" gave no tag (reproduced). `words` now drops a trailing `'s` / `'` from names and text alike (T13).
- F2: " - Outlet" on a Google News title tagged the outlet (reproduced with an alias equal to the outlet). `without_outlet` strips it,
  after a separator only, so a title ending in the same word keeps it (T14).
- F3: `(BSE: 500325)` tagged a company whose symbol is `BSE` (reproduced; BSE Ltd is an F&O underlying). An exchange label beside
  another part is never the symbol; a lone `(BSE)` still is (T15).
