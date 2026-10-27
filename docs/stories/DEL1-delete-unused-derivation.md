# DEL1: delete the unused derivation code (plan, for the orchestrator's check before any deletion)

Owner decision (28 Oct 2026, relayed): corroboration and the article view are derived downstream, so the ~400 lines with no
pipeline caller go (CLAUDE.md "Scope": derivation with no caller and no archive is dead code). Lane 1 (two judges).
Evidence: grep at main 1b1a411 over `fno/ tools/ ops/ .github/ tests/` (strong evidence; re-run in the build).

## Kill-list (no caller outside their own package and their tests)

| Code | Lines | Callers found |
|---|---|---|
| `news/view.py` (`ArticleViewer`, `ArticleView`) | 72 | only `corroboration/flags.py`, `corroboration/origins.py`, `tests/.../test_view.py` |
| `news/origins/{origin,promotional}.py` (`OriginReader`, `PromotionalFilter`) | 102 | only `view.py`, `tests/.../origins/` |
| `news/corroboration/{model,flags,origins}.py` (`corroborate`) | 109 | none outside itself and `tests/.../corroboration/` |
| Tests: `test_view.py` (131), `origins/test_origins_and_promotional.py` (104), `corroboration/test_origins_and_flags.py` (103) | 338 | n/a |

## Stays (live caller) and what it needs

- `resolve/effective_url.py`: used by `cluster/prepare.py`. Its ONLY tests are in `test_view.py` (plant U11), so two tests move
  to a new `tests/ingestion/news/resolve/test_effective_url.py` (same assertions, no viewer), U11 re-pointed there.
- `materiality/terms.py` (`is_material`, U8-U10, U14): used by `reads/order.py`. Untouched.
- `tagging/*`, `news/pin.py`, `reads/*`, `cluster*`, `sources/rules.py::plain_host` (used by resolve/ and article/): untouched.
- Comments in `cluster/similarity.py` and `tests/.../test_labelled_pairs.py` use the word "corroboration" as prose: reworded only
  if they point at deleted code (they do not; left alone).

## DECISION NEEDED: knock-on dead code in the source-rules layer (not on the owner's list)

After the kill-list goes, these `SourceRules` methods have no caller anywhere but their own unit tests
(`tests/.../sources/test_rules.py`): `wire_of_name`, `wire_of_domain`, `is_promotional_provider`, `is_promotional_domain`,
`tier_of`, `outlet_key`, `is_opinion`, `domain_of_label`, `may_upgrade_to_https` (the last four I will re-verify in the build;
`may_fetch` has 5 other callers and stays). The rules FILE sections `wires:` and `promotional:` are then read, validated and
never used (loader `_promotional`, model `Wire`/`Promotional`, `test_safe_pattern` line 53).

- **Option 1 (recommended, reasoning only):** delete those methods in this same change, but KEEP the rules file format and
  loader unchanged. The file is a public rules document; removing sections would change a frozen/public format and is a
  bigger step. Dead methods go; loader stays.
- **Option 2:** also remove `wires`/`promotional` from loader, model and the rules file (a format change; its own story).
- **Option 3:** leave all of it (against the no-dead-code rule).

## Contract rows and plants removed (so no plant guards deleted code)

Rows and plants: U1-U7 (origins), U12, U13, U15, U16, W7b (view), W7-W7, W8, W9, W10, W10b, W11, W11b, W11c, W11d
(corroboration): 22 ids. Re-pointed, not removed: U11. Plants 275 -> 253 (before any Option 1 methods). Rows in
`docs/RECORD_CONTRACT.md` go with them (test_record_contract enforces parity).

## Docs touched

RECORD_CONTRACT.md sections "Origins, promotion and materiality (NP5b)" and "Independent origins (NP6b)" (keep the
materiality rows), stories NP5b and NP6b (mark the removed parts "deleted, DEL1"), NP5/NP6/NP0/NP7 mentions, NEWS_GO_LIVE.md
parked-code line, conversation log open item. Each fact stays in one owning document.

## Gates and proof after deletion

ruff, `tools/check_imports.py`, `tools/check_numbers.py`, full suite, FULL plant runner green at the final SHA, staleness check
(net diff only removals plus the moved effective_url test and the plants file), two judges, merge on the orchestrator's go.

## Sequencing

Do NP9 (title strip) first or after: independent files (`article_file.py`, `tagging/text.py`); I suggest NP9 first, then DEL1 on
the new main so the plants file is merged once.
