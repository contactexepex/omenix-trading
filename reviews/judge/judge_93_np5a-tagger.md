# Judge 93: NP5a tagger (code), round 1 at 29d19cf: FAIL

**Lane 1 (the tagger; it reads the owner's private company list and changes the shared pattern grammar); judge #1.** Branch `story/NP5a-tagger`, frozen SHA 29d19cf. Reviewed `git diff origin/main...29d19cf`: `news/safe_pattern.py`, `news/tagging/{text,dictionary,tagger}.py` (218 lines), the loader and parse changes, rows T1 to T12.

## Gates (locked venv; strong evidence)
1814 passed; ruff is clean; contract plants all `ok`.

## B1 (required; strong evidence, reproduced): a company named in the possessive is never tagged
- `text._WORD = [\w&']+` keeps the apostrophe inside a word, so `Zzalpha's` is the single word `zzalpha's`. It never equals the dictionary key `("zzalpha",)`.
- Reproduced with a two-company dictionary (`Zzalpha Motors` with alias `Zzalpha`, and `Zzbeta`):

| Title | Result |
|---|---|
| `Zzalpha's profit rises` | **nothing tagged** |
| `Zzalpha’s profit rises` (typographic apostrophe; `fold` turns it into the same `'`) | **nothing tagged** |
| `Zzbeta's Q2 beats` | **nothing tagged** |
| `Zzalpha, Zzbeta's results` | only ZZA, **primary, high confidence**. Should be both, as a two-company list, low confidence |
| `Zzalpha Motors' shares fall` | tagged (the bare `'` is outside the word) |

- The possessive is one of the most common headline forms ("X's profit", "X's shares"), so this silently drops a large share of the very items tagging exists for, and skews the confidence of the rest.
- The suite pins the bug: `test_text.py:43` asserts `"l&t's"` is one word.
- The code itself expects a separate possessive: `_LIST_AFTER = ^(?:'s)?\s*[,/]` allows for an `'s` after a hit.
- **Fix:**
  - split or strip a trailing `'s` (and a lone `'`) from a word, keeping `&` inside (`L&T`);
  - or let the name lookup also try the word without its `'s`.
- Pin the table above as tests, plus a plant.

## What holds (strong evidence)
- **Time, measured.** A 2,000-company dictionary, each company with an alias and an exclusion. Every hostile input stays well under 0.1 s (worst 0.028 s):
  - a 1,000-character title of about 160 comma-listed names;
  - names separated by `, x and`;
  - summaries of 20,000 characters made of `<`, `<a`, `a.`, `a-`, `www.` or `&amp;`;
  - names mixed with bare domains.

  The fixed tag and domain cleaners are linear on these. Every pattern sees at most 1,000 characters after cleaning.
- **The widened grammar.** The added literals `# / :` and the escaped `\. \( \)` are single characters outside the group syntax, so they add no ambiguity. `is_safe_pattern` checks the 120-character limit before the grammar match.
- **Matching:**
  - names match as whole words only, longest name first, never overlapping;
  - a symbol matches only in brackets and in capitals (the lookup is case-sensitive against the symbol set);
  - an exclusion removes a hit only when the excluded span contains it;
  - the title is used first, and the summary only when the title names nobody;
  - a list needs two companies (the author's own rule, stated).
- **Privacy.** Pure code: nothing printed, stored or requested.

## Hard lines
No order path, no secret, no Groww call, no request, no write.

## Verdict: FAIL round 1 at 29d19cf. B1 required.
