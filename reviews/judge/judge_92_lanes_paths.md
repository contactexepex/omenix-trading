# Judge 92: the lane-1 path lists, trading `story/x-lanes-paths` 50c6bc7 and dashboard `story/x-lanes-paths` 5cf5ca2

Rule documents are lane 1, so this text needs a PASS. I checked each listed path against the real trees (`fno/*`,
`tools/*` and the dashboard's top-level folders and `web/*`). I also checked the paths that were missing.

## Trading 50c6bc7: FAIL

The text matches judge 91 accurately, so this is not a transcription error. **My own judge 91 list was incomplete.** I
wrote it from memory, not from the tree, and the branch copied it faithfully. These lane-1 subjects (money, outside
services, secrets, records, trade decisions) fall to lane 2 under the list as written:

| Missing path | Lane-1 subject it carries |
|---|---|
| `fno/accounting/`, `fno/costs.py` | money: P&L, charges |
| `fno/nse_margins/` | risk: margin tables |
| `fno/providers/` | outside services (Groww and the other providers) |
| `fno/alerts/` | outside services (Slack) |
| `fno/record_scan/`, `fno/env_file.py` | secrets: the public-record scan, environment loading |
| `fno/research_engine/` | trade decisions and statistics (`statistics.py` is frozen; its neighbours are not) |
| `fno/research_data/` | data availability rules (look-ahead), NSE sources |
| `fno/market_read_models/` | the dashboard publisher (privacy rule) |
| `fno/filings/`, `fno/fo_bhavcopy.py`, `fno/http_pacing.py` | outside services (NSE), politeness limits |
| `fno/config.py`, `fno/models.py`, `fno/freeze_sections.py` | allowed settings, the IST clock, freeze hashing |
| `tools/forecast_golden.py`, `tools/forecast_live_golden.py`, `tools/gdrive_oauth_setup.py`, `tools/nse_raw_download/` | records, secrets, NSE |
| `research/forecasts/`, `research/evaluation/` (hand edits) | forecast and evaluation records |

Must-fix: invert the list. Lane-2 code then needs no list of exceptions at all.
- **Lane 1:** all of `fno/`, `tools/`, `.github/`, `.githooks/`, `.gitattributes`, `config.yaml`, `db/`,
  `requirements*.txt`, the rule documents, and any hand edit under `research/`.
- **Lane 2:** what is left, which is added tests and explanatory docs.

Reason: almost every module under `fno/` carries a lane-1 subject. A list of inclusions will always miss the next new
folder, and I just missed eleven. Any later lane-2 exception inside `fno/` would need my PASS as a rule-document change.

The other refinements (2 to 6) are correct as written.

## Dashboard 5cf5ca2: FAIL

Must-fix:
1. **Screen code is lane 1 by path.**
   - The text makes "any change to what data a screen reads or renders" lane 1. That is the description-based test
     that refinement 1 replaces.
   - `web/app/**` and `web/components/**` are left unlisted, and a `.tsx` change there can render a new field.
   - Proposal: every `.ts`/`.tsx` under `web/` is lane 1. Lane 2 covers only `web/styles/**`, CSS, `design/` and
     added tests under `web/tests/`.
2. **Name every gate and its allowlist, and add the vendored code.**
   - Both allowlists exist: `tools/code_size_allowlist.txt` and `tools/css_duplicate_allowlist.txt`. Put all of
     `tools/` in lane 1.
   - `scripts/` holds third-party vendored JavaScript (`lightweight-charts`), a supply-chain path, so it belongs in
     lane 1 too.
   - `web/tools/` is unlisted.

Correct as written: `api/`, `web/lib/`, `web/app/api/`, middleware, `next.config`, `vercel.json`, `package*.json`,
`config/`, `platform/`, `.github/`, the rule documents, the "Lane 2:" message and the revert rule. All listed paths
exist in the tree.

## Verdict

**FAIL for both.** These are small text fixes. When both lists are corrected, I re-check them against the trees.

## Addendum 1 (14 Oct 2026): re-judge, trading 1290fea and dashboard 03569e7

Both lists are now inverted as asked. I checked them against every top-level entry of both trees. They still leave gaps,
and the cause is the same one as before: lane 2 is defined as "what is left", but some of what is left is not lane 2.

### Trading 1290fea: FAIL (two small must-fixes)

1. **The lanes table in `docs/JUDGE.md` contradicts the refinement.** Row 2 still reads "tests only, docs, refactors
   with no behaviour change, small fixes outside lane 1". `CLAUDE.md` was fixed in 1290fea; this row was not.
2. **Top-level paths that carry lane-1 subjects are still unlisted:**
   - `agents/forecast/*.md`: the AI books' prompts. Changing one changes Book 2 or Book 3's forecasts (records).
   - `playbook/`: the strategy registry and its YAML (trade decisions).
   - `journal/`: paper-account ledgers and positions (money). Job output is lane 3; a hand edit is lane 1.
   - `accounting/`: operating costs (money).
   - `contracts/`: the dashboard API contract (privacy).
   - `.claude/`: the session hooks that switch on the record scan (secrets).
   - `ruff.toml`: a gate's configuration.

Must-fix:
- Replace "Lane 2 is only added tests and explanatory docs" with a closed rule: **lane 2 is only new tests (added
  files or added test cases), and docs outside the rule documents (`README.md`, `reports/`, `research_notes/`, and
  `docs/` outside the rule documents). Lane 3 is as listed. Everything else is lane 1.**
- Fix table row 2 to match.

With that sentence, the path list becomes explanation only. A new folder cannot fall to lane 2 by being forgotten.

### Dashboard 03569e7: FAIL (one small must-fix)

- `web/.npmrc` (the package registry setting: supply chain), `web/tsconfig.json` (compile settings) and `web/public/`
  (served files) are in neither lane.
- Same fix: **lane 2 is only `web/styles`/CSS, `design/` and new tests. Lane 3 is judge files and logs. Everything else
  is lane 1.**

Everything else in both texts is correct.

**Verdict: FAIL for both.** One sentence each. I re-check on the next push.

## Addendum 2 (14 Oct 2026): trading 395324d and dashboard 70cd56d

| Item | Result | Evidence |
|---|---|---|
| Trading: lane 2 is a closed list | MET | Table row 2 and refinement 1 both say lane 2 is "only new tests (added files or cases) and docs outside the rule documents". Everything else is lane 1. The examples include every gap I named: `agents/`, `playbook/`, `journal/`, `accounting/`, `contracts/`, `.claude/`, `ruff.toml`. |
| Trading: no contradiction left | MET | The table, the refinements and the `CLAUDE.md` lane-2 bullet now say the same thing. |
| Dashboard: lane 2 is a closed list | MET | Lane 2 is only `web/styles` and CSS, `design/` and new tests. Lane 3 is judge files and logs. Lane 1 is "everything else", with `.npmrc`, `tsconfig` and `public/` named. |
| Scope | MET | Only `CLAUDE.md` and `docs/JUDGE.md` (trading) and `CLAUDE.md` (dashboard) change. No code changes. |

Follow-up (wording, not blocking): the trading `CLAUDE.md` sentence "Lane 1 is decided by the path list in
`docs/JUDGE.md`" now reads better as "lanes 2 and 3 are listed in `docs/JUDGE.md`; everything else is lane 1". Its
next bullet already says this.

**Verdict: PASS for both.** Merge them. After the merge I check `main`.

## Addendum 3 (14 Oct 2026): merges trading da1509f and dashboard 5a6a2a1 MET

- **Trading da1509f.** Parents are 72a1897 and 395324d. It equals my recomputed `git merge-tree` exactly. Against its
  first parent it changes only `CLAUDE.md` and `docs/JUDGE.md`. No code is on `main` after it.
- **Dashboard 5a6a2a1.** Parents are f74ff60 and 70cd56d. It equals my recomputed merge exactly and changes only
  `CLAUDE.md`. Nothing has landed after it.
- **Skipped full suite.** The orchestrator skipped the full suite for this docs-only diff. That is acceptable: no code
  changed, and checks CI runs on the push anyway.
