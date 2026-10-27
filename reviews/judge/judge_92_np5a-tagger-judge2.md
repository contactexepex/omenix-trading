# Judge 92: NP5a tagger (code, lane 1), judge #2

Frozen SHA `29d19cf` (branch `story/NP5a-tagger`, from main `49537e9`). Reviewed `git diff $(merge-base) 29d19cf`:
- `news/safe_pattern.py`;
- `news/tagging/{text,dictionary,tagger}.py`;
- the changes to `companies/parse.py` and `sources/loader.py`;
- the tests, rows T1-T12 and their plants.

I used invented company names only, here and in my scripts.

**Gates** (in the locked venv): 1814 passed; ruff clean; imports clean (583 files); code size passed; contract plants all
ok.

**My plants (5 of 5 killed):**

| Plant | Tests failed |
|---|---|
| summary used even when the title tags | 15 |
| exclusions ignored | 1 |
| shortest name instead of longest | 2 |
| `versus` ignored | 2 |
| `promotional.text` validated with plain `re.compile` again | 2 |

## Checked and correct

- **The grammar is widened by literals only** (`safe_pattern.py:15`). The loader validates `promotional.text` with it,
  and the shipped file loads.
- **Time on adversarial input:** names are whole-word tuple lookups over at most 1,000 characters; exclusions run in the
  bounded grammar. Twenty tags with a 300-name summary took **0.02 s**.
- **The summary cleaners are bounded:** the tag cleaner never reads past the next `<`, domain labels and counts are
  capped, and the raw text is cut to 20,000 characters before cleaning.
- **Headline first, longest name, exclusion spans and versus demotion** are as described (plants killed).

## Findings (each reproduced with invented names)

1. **F1 (must fix): a possessive hides the company.**
   - `words()` treats an apostrophe as part of a word (`_WORD = [\w&']+`, `text.py:60`), so "Acme's" is one token,
     `acme's`, and never equals the name `acme`.
   - Reproduced: "Acme's profit jumps 20%" gives **no tag**. "Acme Motors' Q2 beats" does tag, because the trailing
     apostrophe is a separate case.
   - The `'s` possessive is one of the most common shapes in headlines, so this costs recall on exactly the
     single-company headlines that would be `high`.
   - Fix: when the dictionary does not know a token, try it again with a trailing `'s` or `'` stripped, in both the
     tagger and `word_tuple`. Keep the apostrophe inside a name (a name of the shape "X Y's" in the list still
     matches). Add a test and a plant.
2. **F2 (must fix): the outlet's name at the end of a title is tagged as a company.**
   - A Google News title ends in " - <Outlet>". `plain_text` drops the trailing source name from the **summary**, but
     the title only goes through `capped` (`text.py:80-81`).
   - Reproduced: the title "Markets close higher - Zztv Profit", with source "Zztv Profit", gives
     `primary=('ZZTV',), confidence='high'` when an alias equals the outlet's name.
   - Indian outlets owned by listed media groups make this realistic: a group's listed name, or an alias the owner adds,
     equals the outlet name (reasoning only). Every story from that outlet would then become a high-confidence primary
     for the media company.
   - The story promises "a link or a source name never becomes a company". Fix: strip a trailing " - <source>" (and
     " | <source>") from the title too, before tagging, and test it.
3. **F3 (must fix): the exchange label in a bracket is taken as a symbol.**
   - `bracketed_symbols` splits `(EXCHANGE: CODE)` on `:` and offers **every** part as a symbol (`dictionary.py:39-41`).
   - Reproduced with an invented exchange-like symbol: "Beta Bank shares (ZZEXCH: 500325) rise" tags `ZZEXCH` as a
     second primary.
   - Indian stories commonly write "(BSE: 500325)" or "(NSE: ..., BSE: ...)". In my understanding a listed exchange
     company trades under the symbol BSE and is an F&O underlying (some evidence; check it against the seed), so it would
     be tagged in every such story.
   - Fix: in a bracket with a colon, take the symbol only from the position that is not a known exchange label (`NSE`,
     `BSE`), and never the label itself. Add a test with the exchange as a listed company.

## Notes (not blocking)

- A two-company list title ("Acme, Beta to merge") leaves no primary. That is defensible for a merger; say so.
- `_LIST_BEFORE` allows up to 60 characters between a comma and "and". "Acme, the lender that bought Beta and ..."
  could demote Beta wrongly. That is fine for the low confidence it gives.

**Verdict: FAIL** (round 1, `29d19cf`). Three small fixes in `text.py`, `tagger.py` and `dictionary.py`.

## Addendum 1

**Round 2 re-review of `story/NP5a-tagger` at `ab4acd2`** (`97cca3f` plus judge 93's B1 table test). I re-derived each
fix myself from the diff `29d19cf..ab4acd2`, reproduced it with invented names, and planted my own mutations.

**Gates (locked venv, `__pycache__` cleared):** `pytest -q -n auto` gave 1817 passed. `ruff check` and
`ruff format --check` were clean. `check_imports` reported 583 files clean, `test_code_size` 3 passed and `check_numbers`
was clean. `tools/contract_plants.py` caught every plant, including the new T13, T14 and T15.

### The three round-1 findings

1. **F1 (possessive): fixed.**
   - `words()` drops a trailing `'s` or `'` from each word (`text.py:59-66`). `word_tuple` reuses it, so names and text
     fold the same way.
   - Reproduced:
     - "Zzalpha's profit jumps 20%" tags ZZAL, high.
     - "Zzalpha Bank's profit" tags ZZAB, the longest match still wins.
     - "ZZ&LT's shares" and "Zz & Lt Works's shares" tag ZZLT.
     - "Zzalphas' rise" tags nothing. A plural is not the name.
   - The end position is the stem's end (`("acme", 0, 4)`), so exclusion spans and list detection stay correct.
2. **F2 (outlet suffix): fixed for the case found.**
   - `without_outlet()` strips a trailing source name only when it follows whitespace and a separator (`-`, `–`, `—`
     or `|`). The match ignores case.
   - Reproduced with source "Zzalpha":
     - "Markets close higher - Zzalpha", the en-dash and em-dash forms, and "— ZZALPHA" all tag nothing.
     - "Markets rally as Zzalpha" still tags ZZAL.
     - "Results: Zzbeta - Zzalpha" tags ZZBE only.
     - "Zzalpha - Zzalpha" tags ZZAL from the headline.
3. **F3 (exchange label): fixed.**
   - `_candidates` (`dictionary.py:50-57`) handles three shapes:
     - A lone part is a symbol, so "(BSE)" still tags the listed company BSE.
     - In a two-part bracket that starts with NSE or BSE, only the second part is a candidate, so "(NSE: BSE)" tags BSE.
     - Otherwise an exchange label is never a candidate.
   - Reproduced:
     - "(BSE: 500325)" and "(bse: 500325)" tag nothing.
     - "(BSE:500325, NSE: ZZDE)" tags ZZDE only.
     - "(BSE, NSE)" tags nothing.

### My plants (each restored afterwards)

| Plant | Mutation | Result |
| --- | --- | --- |
| P1 | drop the "ends with a separator" check | caught (1 failed) |
| P2 | drop the "whitespace before the name" check | **survives** |
| P3 | `(NSE: X)` returns nothing | caught (2 failed) |
| P4 | possessive `'s?$` becomes `'s$` | caught (1 failed) |
| P5 | the end position becomes `match.end()` | caught (1 failed) |
| P6 | a lone `(BSE)` is dropped too | caught (1 failed) |
| P7 | the outlet match becomes case-sensitive | **survives** |

### Notes (not blocking)

- **N1, test gaps.** The P2 and P7 behaviour is correct by my reproduction ("— ZZALPHA" is stripped). No test pins
  either, so a later edit could drop them silently. Suggested additions:
  - "Merger of Zzbeta-Zzalpha" with source "Zzalpha" keeps ZZAL (P2);
  - an upper-case outlet suffix (P7).

  Either can go in the next push that already touches these files.
- **N2, outlet name variants (reasoning only).** Three variants are not stripped:
  - a title with trailing whitespace ("... | Zzalpha ");
  - a source that differs from the suffix ("The Zzalpha" against "- Zzalpha");
  - a missing source.

  Google News normally gives the `<source>` text identical to the suffix, and feed parsers strip whitespace, so I
  expect this to be rare. NP5b's caller must pass `source`, and I check that in the NP5b review.
- NP5a has no production caller of `Tagger.tag` yet, so the effect on the Record comes only through NP5b.

**Verdict: PASS** (round 2, `ab4acd2`).
