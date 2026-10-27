# Judge 118: DEL1 delete unused derivation (code), round 1 at d3b9f04: PASS

**Lane 1, two judges; this is judge #1.** Branch `story/DEL1-delete`, frozen SHA d3b9f04. Its code is the same as 15976a7; d3b9f04 only merges judge files from `main`. I reviewed `git diff origin/main...d3b9f04`: 26 files, +142/−1018.

## Gates (strong evidence)
In a venv installed from `requirements.lock`:
- 1984 passed;
- ruff check and format are clean, and check_imports is clean;
- **plant runner: 251 of 251 `ok`**, nothing unnoticed.

## Nothing live was deleted (strong evidence, searched at d3b9f04)
- **The only production file changed is `sources/rules.py`.** Every other `fno/` change is a whole-file deletion of `view.py`, `origins/` or `corroboration/`. So no live call site was edited away along with its callee.
- **No deleted name remains anywhere in `fno/`, `tools/`, `ops/` or `.github/`:**
  - `tier_of`, `outlet_key`, `may_upgrade_to_https`, `is_opinion`, `domain_of_label`, `wire_of_name`, `wire_of_domain`, `is_promotional_provider`, `is_promotional_domain`, `HOST_PREFIXES`;
  - `ArticleViewer`, `ArticleView`, `corroborate`;
  - the `news.view`, `news.origins` and `news.corroboration` imports.
- **The live questions stay:**
  - `may_fetch` (reads, pages, probe);
  - `lookup` and `plain_host`;
  - `normalise_label` (still used by `companies/parse.py`);
  - `effective_url` (used by `cluster/prepare.py`). Its tests moved to `tests/ingestion/news/resolve/test_effective_url.py` with the same assertions, U11 is re-pointed there and is `ok`.
- **Kept on purpose.** The rules file, the loader and the models are unchanged: tier, `https_links`, `opinion_unless_path`, `wires:` and `promotional:` are still parsed. That matches the orchestrator's decision and CLAUDE.md's scope text ("a consumer ... reads the Drive Record and the public rules itself"). The file is the public rules; only the classifying code is gone.

## Scope and standards
- **Scope.** CLAUDE.md's scope section treats derivation with no pipeline caller and no archive as dead code, and this deletes exactly that.
- **Contract rows.** 24 rows and plants went with their code (U1–U7, U12, U13, U15, U16, W7b, the W7–W11d family, O4, O8, O14). `test_record_contract` keeps the rows and plants in step, and the runner's count fell from 275 to 251, as the plan says.
- **Remaining coverage.** U15 and U16's behaviour still lives in the read pass and is covered by M3, M21, Z1, Z1b and U14.

## Note (not blocking)
- **N1.** `model.py` keeps `UNLISTED`, `TIERS` and the outlet fields that no ingestion code reads now. They are the public rules' schema, kept on purpose, so say so in `model.py`'s docstring. Otherwise a later "no dead code" pass will propose deleting them.

## Hard lines
No orders, no Groww, no secret. No Record or workflow change.

## Verdict: PASS round 1 at d3b9f04.
