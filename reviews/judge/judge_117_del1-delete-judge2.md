# Judge 117: DEL1 delete the unused derivation code (judge #2, code)

**Subject:** `story/DEL1-delete` at `d3b9f04` (the implementer says the code is identical to `15976a7`). 26 files,
142 lines added and 1,018 removed.
- What it does:
  - deletes `news/view.py`, `news/origins/` and `news/corroboration/`, with their tests;
  - deletes nine proven-dead `SourceRules` methods and the attributes and constants only they used;
  - moves the `effective_url` tests to `tests/ingestion/news/resolve/test_effective_url.py`;
  - removes 24 contract rows and plants.
- Lane 1: rules and contract rows.

**Owner decision:** on record. `conversations/2026-10-28.md:43` holds "get rid of these 400 unused lines." with the
decision. **Scope:** it applies CLAUDE.md's no-dead-code test.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 1984 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 624 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

## What I checked (*strong evidence*)

- **No dangling reference.** I grepped `fno tests tools ops .github` (`.py`, `.yml`, `.sh`, `.json`) for each deleted
  name. Every one returns 0:
  - `ArticleViewer`, `ArticleView`, `OriginReader`, `PromotionalFilter`, `corroborate`;
  - the nine methods;
  - `_wire_name`, `_promo_providers`, `_label_domain`, `LABEL_IS_A_HOST`, `HOST_PREFIXES`;
  - the three module paths.
- **Two survivors of the grep, both still in use:**
  - `UNLISTED` is still used by `sources/model.py`'s `TIERS`.
  - `normalise_label` is still used by `companies/parse.py` and `companies/seed.py`, so `labels.py` is not dead.
- **What stays is live:**
  - `may_fetch`, `lookup` and `plain_host` have callers in the fetcher, the probe, the read links, resolve and article;
  - `effective_url` is used by `cluster/prepare.py`;
  - the rules file, the loader and the models stay, because the public rules are read downstream.
- **The moved `effective_url` tests still bite:**
  - D1: always taking `canonical_url` fails 4 tests;
  - D2: falling back to the feed's `source_domain` fails 2 tests. That is judge 94 B1, still pinned.
- **The source of the deleted view lives on in the read pass and the cluster run.** The existing plants M3, M21, Z1,
  Z1b and U14 pin it, and they are in the green runner.

## Notes (not blocking)

- **N1: `Outlet.https_links` and `opinion_unless_path` are parsed but read by nothing here.** They are consumer-facing
  rule fields in the public rules file, and the scope rule lets the consumer read the public rules. Keeping them is
  consistent; say it once in `NP1-source-rules.md` so nobody re-adds a reader here.
- **N2: the parked-code note on wire detection (judge 115 N1) is moot,** because `OriginReader` is deleted.

**Verdict: PASS** (round 1, `d3b9f04`).
