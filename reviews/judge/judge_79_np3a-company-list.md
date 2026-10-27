# Judge 79: NP3a company list (code), round 1 at 6504962: FAIL

**Lane 1 (company list, privacy); judge #1.** Branch `story/NP3-company-list-and-feed-planning`, frozen SHA 6504962. Reviewed `git diff origin/main...6504962`: `fno/ingestion/news/companies/*`, `news/versioned.py` (extracted from `feeds.py`), codes, rows Q1 to Q7.

## Gates (strong evidence)
In a venv installed from `requirements.lock`: 1506 passed. ruff and check_imports are clean, and contract plants are all `ok`.

## B1 (required; strong evidence, measured): the ReDoS guard on exclusions lets catastrophic patterns through
- `parse.py` refuses only a quantifier after a group (`QUANTIFIED_GROUP = \)\s*(?:[*+{]|\?\?)`). It blocks `(a+)+$`, but polynomial backtracking needs no group.
- Both of these patterns are **accepted** by `_exclusions` and are under the 120-character cap. Times for `re.search(pattern, "a" * n)`, with no match:

| Pattern | n = 25 | n = 50 | n = 100 |
|---|---|---|---|
| `.*.*.*.*.*.*x` | 0.02 s | 1.06 s | **56.9 s** |
| `\w*\w*\w*\w*\w*\w*!` | 0.03 s | 1.98 s | **> 60 s** (killed) |

- 100 characters is an ordinary headline length. One such exclusion in the owner's private list (a typo is enough) would hang every tagging run.
- The story claims a ReDoS restriction at the owner-pattern entry, and this guard does not provide it.
- **Fix.** Blacklisting shapes cannot work. Use an allow-list instead, for example:
  - exclusions are literal phrases, matched case-insensitively with word boundaries (`re.escape`); or
  - a small whitelisted grammar: literals, `\b`, `\s+`, alternation, `?` on a single character, and no `*`, `+` or `{}` except `\s+`.
- Pin it with the two patterns above as tests, plus a plant.

## B2 (required, small; strong evidence, reproduced): the seed is written without passing the parser it must pass
- `seed_companies(apply=True)` writes `companies-v1.json` once and never replaces it, but it never runs `parse_company_list` on its own bytes first.
- `build_seed` takes Nifty 500 symbols unchecked against `SYMBOL`. A Nifty 500 row whose symbol is 22 letters long gives a seed that `parse_company_list` refuses (`company_list_invalid`). That file would then be the unusable first version.
- The renamed second name (when two cleaned names collide) is also not checked against the names already taken.
- Real NSE symbols are short, so this is unlikely, but the file is write-once, and the fix is one line: parse the seed before `put`, and stop with a fixed code if it fails.

## What holds (strong evidence)
- **Privacy:**
  - the printed line is counts plus a fixed code (plant leaking the first 80 bytes of the seed → 1 failed);
  - every refusal is one fixed code that names no symbol or name;
  - `test_no_company_or_discovery_list_is_ever_in_the_repository` scans the whole tree for `companies-v*.json` and `discovery-v*.json`;
  - the only names in code are the four public index aliases, as declared.
- **Never overwrites:** any file already in the companies folder stops the seed (plant removing the guard → 1 failed).
- **Structure:**
  - `CompanyListSource` interface, a single adapter, and a composition root;
  - `VersionedFiles` extracted with the feed tests unchanged;
  - every file is under 100 lines.
- **ReDoS shape check:** removing it → 5 failed. So the existing check is pinned; it is simply too narrow (B1).

## Minor (requested)
- **M1.** The name order "EQUITY_L > Nifty 500 > F&O master" is not pinned. My plant swapping the first two passes all 52 tests, because in the fixture both lists give the same Apollo name once cleaned. Give the fixture a symbol whose names differ between the two lists.

## Hard lines
No order path, no secret, no Groww call. No company list is in the repository or in any printed line.

## Verdict: FAIL round 1 at 6504962. B1 and B2 required; M1 requested.
