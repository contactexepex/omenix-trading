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
