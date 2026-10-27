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

## Addendum 1: superseded by c5aeb93: PASS, on condition of one stated limit

Reviewed `git diff 6504962 c5aeb93`, which folds in judge 78's F1 to F3; they overlap my B1 and B2.

**Gates (locked venv).** 1514 passed; contract plants all `ok`, Q1 to Q10.

**B1 is fixed for the realistic case.**
- A cap of 2 open repeats (`*`, `+`, `{n,m}`) and 4 optionals now refuses both of my round-1 patterns: `.*.*.*.*.*.*x` and `\w*\w*\w*\w*\w*\w*!`.
- `.*.*x` is accepted and runs in under 1 ms on 100 characters.

**But the guard is still a heuristic (strong evidence, measured).** Ambiguous alternation needs no repeat at all.

| Pattern | Length | Guard | Time on `"a" * 100` |
|---|---|---|---|
| `(a\|a)` × 16 + `x` | 81 | accepted | 0.16 s |
| `(a\|a)` × 20 + `x` | 101 | accepted | 2.7 s |
| `(a\|a)` × 23 + `x` | 116 | accepted | **20.3 s** |

**Why I accept it anyway (reasoning only).**
- This needs about 17 or more ambiguous alternatives in a row: not a plausible typo.
- The file is written only by the owner, with no outside attacker.
- The `.*`-chain mistake, which is plausible, is now stopped.

**Condition (text only, the orchestrator can check):** the story and `parse.py`'s docstring must state the limit. "The guard stops chained open repeats; it is a heuristic, not proof against a deliberately ambiguous pattern (for example a long run of `(a|a)` groups); exclusions are owner-written." A per-headline time limit, or literal-only exclusions, is the follow-up if that is ever not acceptable.

**B2 fixed.** `build_seed` skips and counts rows the list checks would refuse (odd symbol, empty or long name, a name taken twice). It then runs `parse_company_list` on its own bytes before returning, and `seed_companies` maps a refusal to `company_list_invalid`. So no unreadable v1 can be written.

**M1 still open (requested, not a condition).** Swapping the EQUITY_L and Nifty 500 name order still passes all 60 tests.

**Verdict: PASS at c5aeb93, on condition of the stated limit.**

## Addendum 2: round 2 at 1a1e5d6: PASS, nothing left open (this supersedes Addendum 1's condition)

Reviewed 1a1e5d6. Exclusions are now an allow-list grammar (`EXCLUSION_GRAMMAR`, fullmatch): plain text, `(?:A|B)` groups of plain text, `x?`, and one trailing `\w*`. At most 4 `?` per pattern.

**Gates (locked venv).** 1515 passed; ruff and check_imports are clean; contract plants all `ok`.

**B1 fixed (strong evidence, attacked).**
- Refused:
  - `.*.*x` and `\w*\w*\w*!`;
  - `(a|a)x`, because capture groups are not in the grammar;
  - `a?b?c?d?e?`, a fifth optional;
  - my round-1 alternation bypass, `(?:a|a)` × 16 + `x`. Every `(?:` spends one of the 4 `?`, so a pattern holds at most 4 groups.
- **The worst shape I could build that is accepted:** 4 groups of 13 identical alternatives, 117 characters.
  - It costs 0.08 s on 300 characters, 0.28 s on 1,000 and 1.43 s on 5,000: linear in the text, with a bounded constant (13^4).
  - That is acceptable for owner-written patterns.
- Realistic patterns are accepted: `Mahindra(?: Finance| Lifespace)`, `Tata (?:Steel|Power)\w*`.

**B2 fixed (see Addendum 1).**

**M1 fixed.** My swap plant (the Nifty 500 name before EQUITY_L) now fails a test.

**Verdict: PASS round 2 at 1a1e5d6.** The "state the limit" condition of Addendum 1 no longer applies: the grammar replaces the heuristic.
