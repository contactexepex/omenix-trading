# Judge 95: NP5b origins, promotional filter, materiality and the article view (code, lane 1), judge #2

Frozen SHA `691f315` (branch `story/NP5b-origins-and-materiality`, branched from NP5a `29d19cf`, with NP4b merged in).
Reviewed `git diff 29d19cf 691f315` for NP5b's own files:
- `news/origins/{origin,promotional}.py`;
- `news/materiality/{terms,file}.py`;
- `news/view.py`;
- the new codes.

I used invented names only.

**Gates** (in the locked venv): 1915 passed; ruff clean; imports clean (608 files); code size passed. Contract plants:
all ok **except H7**, which is "unnoticed" on this branch (see the note).

**My plants (4 of 4 killed):**

| Plant | Tests failed |
|---|---|
| `is_material` without the high-confidence rule | 2 |
| the view's URL taken from the wrapper link | 2 |
| byline origin off | 3 |
| promotional phrases off | 3 |

## Checked and correct

- **The view is computed on read and stores nothing.** Its URL comes only from the resolution file or the publisher's
  own link, never from a label or a page: spoof-resistant, and the plant is killed.
- **Origins come from facts only:** an agency's own domain, then the provider, then the bylines, then a title
  attribution, all against the public wire rules.
- **The promotional filter** checks providers, labels and bylines, then domains, then the shipped phrases. The phrases
  are compiled with the safe grammar and run on capped text.
- **Materiality** is a private versioned file in the shared discipline. Its patterns are in the safe grammar; weights
  must be in (0, 10] and not `bool`; a repeated term is refused; at most 200 terms.

## Findings

1. **F1 (must fix): materiality is inflated by the outlet name at the end of a Google News title.**
   - `MaterialTerms.weight` matches against `capped(title)` (`terms.py:41-43`), and that keeps " - <Outlet>".
   - Reproduced: with the term `Profit` (weight 1), "Acme Motors names new chief - Zztv Profit" weighs **1.0** and is
     **material** (with a high-confidence tag). The same title without the suffix weighs 0.
   - Every story from an outlet whose name holds a material term would be pushed up the page-read queue.
   - It is the same root cause as judge 92 F2 (the tagger). Fix it once: a shared "title without its trailing source
     label" for the tagger **and** materiality. Keep the raw title for `attributions()` in `origin.py`. There the
     trailing label is used on purpose, because a Google News title whose outlet is the agency is that agency's copy.
2. **F2 (must fix): it carries NP5a's three open defects.** This branch is built on `29d19cf`, so the article view
   inherits judge 92's F1 (possessives never tag), F2 (the outlet suffix tags a company) and F3 (an exchange label in
   a bracket tags a company). The view's `tag` and `material` fields are wrong in those cases. NP5b needs NP5a's fixes
   brought in before it can pass.

## Note (not blocking)

**The H7 contract plant is stale on this branch.** Its `old` string, `self.stopped.add(host)`, now occurs 3 times in
`pages/fetcher.py`, so the plant lands on the wrong line and nothing notices. NP4b's head (`98ad64a`) already has the
re-pointed plant (one occurrence). Merging main or NP4b's final version into this branch fixes it, and
`contract_plants.py` must then be all ok.

**Verdict: FAIL** (round 1, `691f315`).

## Addendum 1

**Round 2 re-review of `story/NP5b-origins-and-materiality` at `1002195`.**
- The branch is stacked on NP5a `ab4acd2`, which I passed in judge 92 Addendum 1, so NP5a is settled.
- The `tagging/` package is byte-identical to `ab4acd2`.
- Also in this head: judge 94's B1 (no URL means no host, plant U13) and the H7 entry from main.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 1920 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 608 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught, including U14, U15, U13 and the re-pointed U8 and U10.

### Round-1 findings

1. **F1 (the outlet suffix inflates materiality): fixed.**
   - What changed:
     - `MaterialTerms.weight` and `is_material` take `source` and apply NP5a's shared `without_outlet` (`terms.py:41-47`).
     - `ArticleViewer.view` passes `article.source` (`view.py:63`).
   - Reproduced with the invented term "profit" (weight 1) and source "Zztv Profit":

     | Title | Round 1 | Round 2 |
     | --- | --- | --- |
     | "Zzalpha shares rise - Zztv Profit" | weight 1.0, material | weight 0, not material |
     | "Zzalpha profit rises - Zztv Profit" | material | weight 1.0, still material (the word is in the story) |

   - Without a source the suffix still counts, the same limit as judge 92 N2. The production caller always passes
     `article.source`.
2. **F2 (inherited NP5a defects): fixed** by the merge of NP5a `ab4acd2`.
   - "Zzalpha's profit jumps" now tags with high confidence and is material.
3. **H7 note: resolved.** The H7 `old` text now matches the refusal branch in `pages/fetcher.py`, and the plant runner
   catches it.

### My plants (each restored afterwards)

| Plant | Mutation | Result |
| --- | --- | --- |
| Q4 | `is_material` stops passing `source` to `weight` | caught (3 failed) |
| Q6 | `view` calls the tagger without `article.source` | **survives** |
| Q7 | the promotional filter skips the summary | caught (2 failed) |

### Notes (not blocking)

- **N1, test gap (Q6).** The view wiring is correct today. No test pins that the view passes `article.source` to the
  tagger, yet that argument is the only production path for judge 92 F2 (the outlet name tagging a company). Dropping
  it would bring F2 back with every test green.
  - Suggested test: a view of "Markets close higher - Zzalpha" with source "Zzalpha" has no tag.
  - Add it in the next push that already touches these files.
- **N2, promotional filter (reasoning only).** It still reads the full title, outlet suffix included, as the
  implementer said.
  - The shipped phrases are vendor boilerplate: "Zacks Rank #", "sponsored content|post", "advertorial" and the like.
    None is plausibly part of an outlet's name.
  - A false hit would only stop an article counting as an independent origin. That is the conservative direction. No
    change needed now.

**Verdict: PASS** (round 2, `1002195`).
