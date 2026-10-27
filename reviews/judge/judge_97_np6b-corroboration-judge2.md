# Judge 97: NP6b corroboration read-model (judge #2, code)

**Subject:** `story/NP6b-corroboration` at `e7ff690` (two commits on main).
- New package: `fno/ingestion/news/corroboration/` (`model.py`, `origins.py`, `flags.py`; 109 lines).
- `ArticleView` gains `wire_via` and `outlet`.
- Rows W7 to W11b, and the story `docs/stories/NP6b-corroboration.md`.
- Lane 1: it decides what the dashboard calls corroborated. It writes nothing, makes no request, adds no workflow and
  changes no Record byte, which I checked in the diff.

**Gates (locked venv, `__pycache__` cleared):**
- `pytest -q -n auto`: 1930 passed.
- `ruff check` and `ruff format --check`: clean.
- `check_imports`: 614 files clean.
- `test_code_size`: 3 passed.
- `check_numbers`: clean.
- `tools/contract_plants.py`: every plant caught.

## Against the plan (judge 96, round 2)

- **Labels match the plan** (`origins.py:19-20`): `wire:<agency>` when there is an agency, else
  `outlet:<outlet key>`.
  - `outlet_key` joins `same_as` hosts and strips `www.`, `m.`, `amp.` and `mobile.` (`sources/rules.py:58-67`).
  - `wire_of_name` returns the agency's canonical name, so two spellings of one agency are one group.
- **Countable** (`origins.py:23-25`): listed, not promotional, not opinion.
- **Verified** (`origins.py:28-30`): countable, and either read (`full`, `partial` or `paywalled`) or an agency whose
  `via` is not `title`. That is plan item 7, done as written.
- **The counts and flags follow the plan:**
  - `independent_origins` is the number of verified groups;
  - `unverified_origins` is the number of countable groups that are not verified;
  - the seven flags fire in a fixed order, one rule each.
- **Purity:**
  - groups are sorted by label and keys inside a group are sorted;
  - the permutation test covers every order of three views;
  - nothing is stored.
- **Traceability:** `reads_used` and `rules_version` are present. `rules_version` defaults to `""`, and the caller
  (NP7) must supply it. This is stated in the story.

## My plants (each restored afterwards)

| Plant | Mutation | Result |
| --- | --- | --- |
| R1 | `promotional_provider` never fires | caught |
| R2 | `no_vetted_origin` never fires | caught |
| R3 | `origins_unverified` never fires | caught |
| R4 | `opinion` never fires | caught |
| R5 | `low_tier_only` never fires | caught |
| R6 | `verifies` no longer requires a countable view | caught (2 failed) |
| R7 | `reads_used` counts only successful reads | **survives** |
| R8 | a group is countable only when ALL its views are | **survives** |
| R9 | `paywalled` no longer counts as read | caught |
| R10 | the view's `outlet` is the raw host, not the outlet key | caught (2 failed) |

## Notes (not blocking)

- **N1, test gaps (R7, R8).** The code is correct as written in both cases.
  - **R7:** no test has a read file whose access failed (`blocked`) and checks that it still counts in `reads_used`.
  - **R8:** no test has one outlet group holding a promotional unread view and a countable unread view. That is the
    case where `any` against `all` changes `unverified_origins` and the `origins_unverified` flag.

  Add both to the next push that touches these files.
- **N2, title-attributed wires (reasoning only).** A wire named only in the title still sets the group LABEL, even
  though it does not verify.
  - Two outlets that each end a title with the same agency are one origin, not two. That errs on the side of
    under-counting, which is acceptable.
  - The heuristic can never raise `independent_origins`.
- **N3, empty outlet key.** The story says it plainly: unlisted views with no host share the label `outlet:`. They
  never count. The dashboard must not show that group as an outlet; that is NP7's job.

**Verdict: PASS** (round 1, `e7ff690`).
