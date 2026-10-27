# Judge 94: NP5b origins, promotional and materiality (code), round 1 at 691f315: FAIL

**Lane 1; judge #1.** Branch `story/NP5b-origins-and-materiality`, frozen SHA 691f315. It is **stacked on NP5a at 29d19cf, which I failed (judge 93)**, so, per the orchestrator, no verdict here is final until NP5a is settled and NP5b is rebased.

Reviewed NP5b's own files, `git diff 29d19cf 691f315`: `materiality/{terms,file}.py`, `origins/{origin,promotional}.py`, `view.py`. NP4b's files also appear in that diff through the merge of `main`; they were reviewed in judge 91.

## Gates (locked venv)
- 1915 passed; ruff is clean.
- **Contract plants: H7 is NOT caught on this branch** ("the plant went unnoticed").
  - The branch's `tools/contract_plants.json` still has the **old** H7 text, `self.stopped.add(host)` → `pass`. Since NP4b, the fetcher has three such lines (refusal, a second stop, timeout), so the plant changes the wrong one.
  - `main` already carries the updated H7 (it anchors on the `STOP_STATUSES` line).
  - A merge artifact: take `main`'s `contract_plants.json` entry when rebasing, and show `contract_plants.py` all `ok`.

## B1 (required; strong evidence, reproduced): an unresolved item's tier and wire come from the domain the feed claims
- `ArticleViewer.view`: when there is no resolution and no publisher link, `host = plain_host(article.source_domain)`. That is the domain Google's `<source url>` *claims*. It then sets `tier`, `listed`, `opinion`, `wire` (by domain) and `promotional` (by domain).
- Reproduced with the real `SourceRules`. An unresolved wrapper article that claims `reuters.com` comes out as:

  ```
  url '' | host reuters.com | tier tier1 | listed True | wire Reuters
  ```

- That contradicts NP0 section 3, which judge 70 passed. The tier "is computed on read from the host of that URL through the allowlist, never from a label alone; an item with no resolution file has tier `unlisted` and is not counted as an origin until it is resolved"; and "the feed's claimed `source_domain` is only a hint and a cross-check".
- That was decision 5 (stricter than agentic). This code is agentic's looser behaviour, and NP6 would count these unresolved items as vetted origins.
- **Fix:**
  - with no effective URL, `host` stays `""`, giving `tier unlisted`, `listed False` and no domain-based wire or promotion;
  - keep `source_domain` only as a separate hint field if the dashboard needs it;
  - pin it with this case, plus a plant.

## What holds (some to strong evidence; read and partly probed)
- **Material terms** use the one safe grammar, at most 200 terms, weights in (0, 10] and never a bool, run against at most 1,000 characters. Material means weight ≥ 1 *and* a high-confidence single-company title. The terms file is private and versioned like the others, with fixed error codes.
- **Origin.** In order: agency domain, provider, byline, title attribution (the last bracketed label, or the last label after a dash or bar, each at most 40 characters, on at most 1,000 characters). The regexes are bounded.
- **Promotional.** It checks providers, byline and source label, then the promotional domain, then the shipped phrases (compiled with the safe grammar) on the title and the cleaned summary.
- **The view is pure:** nothing is stored. The source URL comes only from the resolution file or the publisher's own link, which is correct when one exists.
- It inherits NP5a's possessive defect (judge 93 B1) wherever it tags.

## Hard lines
No order path, no secret, no Groww call, no request, no write.

## Verdict: FAIL round 1 at 691f315. B1 and the H7 plant required. Re-review after NP5a is settled and NP5b rebased.

## Addendum 1: round 2 at fb94003: PASS

Reviewed fb94003. It is stacked on NP5a ab4acd2 (judge 93 PASS) and has `main` merged in.

**Gates (locked venv).** 1918 passed; ruff is clean; contract plants all `ok`, including H7 (now `main`'s entry) and U11 to U13.

**B1 fixed (strong evidence, my reproduction re-run).**
- `view.py`: with no effective URL, `host = ""`; the claimed `source_domain` is not used.
- An unresolved wrapper claiming `reuters.com` now gives: url `''`, host `''`, tier `unlisted`, listed False, wire `''`, promotional False.
- An agency named in the title or byline can still mark a wire: those are the item's own facts, not a claimed domain, which matches NP0.
- Plant U13 pins it.

**The merge artifact is fixed.** H7 is `main`'s entry and is caught.

**Verdict: PASS round 2 at fb94003.** It merges after NP5a.

## Addendum 2: 1002195: PASS

Reviewed `git diff fb94003 1002195`.
- **The change:** `MaterialTerms.weight` and `is_material` take the source and drop a trailing " - Outlet" through the shared `without_outlet`, so a term in the outlet's name never makes a title material (judge 95 F1). `view.py` passes `article.source`.
- **Plants:** U14 and U15 are new; U8 and U10 are re-pointed.
- **Gates (locked venv):** all tests pass; ruff is clean; contract plants all `ok`.

**Verdict: PASS at 1002195.**
