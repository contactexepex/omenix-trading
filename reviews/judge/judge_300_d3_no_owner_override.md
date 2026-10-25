# Judge 300: D3 refuses an owner override in every book (story/d3-no-owner-override at b49abdde)

**Verdict: PASS for the code at b49abdde. Lane 1 (it changes the decision-record schema).** This is judge E's range,
300-349 (orchestrator, 16 Oct). The orchestrator has said a new head will follow, amending F4's owner-override text.
That head needs a short addendum before the merge: a docs-only diff on top of b49abdde, which I will check against row
229 and F4's criteria 2-3.

**Later head e5906769 (11:21):** this is a merge of `main` only. The branch's own diff against `main` is the same
five files, byte for byte, so this verdict covers it too; the merged tree is gated at the merge (JUDGE.md, merge
procedure). No F4 amendment yet.

## Story check
- **Owner decision** (strong evidence). `docs/DESK_DECISIONS.md` line 229, "D4/D5: the five design questions
  accepted as recommended" (owner: "Accept all five (Recommended)"), item (4): "D3 refuses any non-empty
  owner_override for every book (no overrides on paper)". The change implements exactly that.
- **Register:** the builder (01SFDjjZ) is the D4/D5 owner, and D3c was unowned before this. No overlap found.
- **Story text:** `docs/stories/D-playbook-decisions.md`'s field list now says `owner_override` is always null, and
  why. It adds no new numbered acceptance criterion; see minor 2.

## Criteria (own evidence)

| Criterion | Builder's claim | Judge's evidence | Result |
|---|---|---|---|
| Any non-null `owner_override` is refused in every book | 9 parametrised cases (3 books × link, `""`, mapping) | `decision_record.py:153-155`. Each case passes with null and is refused with the value. Mutation 3 (empty `ALWAYS_NULL`) fails all 9 | MET |
| The refusal runs on the write path | (implicit) | `decision_store.py:69-70`: `DecisionStore.write` validates every record before writing anything. It is the only caller of `validate_record` in `fno/` (grep) | MET |
| Nothing writes the field today | `decision_run.py:29` carries it as run context, null | Read: `RUN_CONTEXT` copies it from the run context, which D3's run builds as null. No writer in `fno/` sets it (grep `owner_override`) | MET |
| Book 3's day record alone may leave `strategy_id`/`strategy_spec_sha256` null | new test, plus a mutation | `decision_record.py:148-149`. Mutation 2 (exemption for every record) fails the test, so a Book 3 opportunity record with no strategy is still refused. Mutation 4 (exemption widened to Book 2) is also caught | MET |
| Empty string refused (deviation from "non-empty") | reasoning | Accepted. Null is the schema's only "absent", and `""` is no link. Mutation 1 (truthiness instead of `is not None`) fails 3 cases (`""` in each book) | MET |
| C2's brake restart (`owner_overrides.csv`) untouched | stated | Diff: no file under `fno/risk/` changed. The brake restart is a risk control, not a decision override (JUDGE.md, "Brake restarts") | MET |

## Gates (run myself on b49abdde, fresh worktree, unshallowed)
- `env -u FNO_SLACK_BOT_TOKEN PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider -n auto`: **7465
  passed** (2 warnings, 207.9 s).
- `ruff check fno tests tools`: all checks passed. `ruff format --check fno tests tools`: 1336 files already formatted.
- `python tools/check_imports.py`: exit 0. `python tools/check_records.py`: clean (1426 files).
- Sizes: `decision_record.py` and `tests/decisions/test_records.py` are both well under 350 lines.

## My mutations (all restored; `git status` clean afterwards)
1. `is not None` → truthiness: 3 failed (the `""` cases).
2. Day-record exemption applied to every record: 1 failed.
3. `ALWAYS_NULL = ()`: 9 failed.
4. Day-record exemption widened to Book 2's `rule_default`: 1 failed.

## Claims vs reality
- "Every book refuses it": true (cases, plus mutation 3).
- "Nothing that writes records sets it": true (grep, `decision_run.py:29`).
- "The scoreboard's override check now always reads no override": true. `fno/scoreboard/sources.py:43-47`
  `RecordedOwnerOverride` returns `bool(None)`, which is False (see minor 1).
- "Removing the day-record rule fails the test": true (mutation 2).

## Hunting
- **No path re-enables an override:** `LINKS` still lists `owner_override` as nullable, but `ALWAYS_NULL` runs after
  the emptiness check, so any value is refused whatever `LINKS` says. Old records are not re-validated on read, and
  no committed record carries the field non-null (no Book 1 record exists on `main` yet).
- **Money safety:** the change only refuses records; it cannot enlarge a trade or bypass a limit. There is no order
  path.
- **Frozen files:** `fno/playbook/decision_record.py` is not in a freeze list I could find (`git grep` over
  `research/evaluation/` and the freeze manifests found no mention).

## Findings
No blocking or should-fix findings.

Minor:
1. `fno/scoreboard/sources.py:43-47`: `RecordedOwnerOverride`'s docstring still says "which F4 fills", and its check
   can now only return False. It belongs to S2's owner. Remove it, or fix the docstring, in S2's next change. The
   orchestrator should note it.
2. The D3 story text records the rule only in the field list. The Book 3 day-record exemption
   (`DAY_RECORD_NULLABLE`) is in neither the field list nor criterion 6. Add one sentence to criterion 6 with the next
   D3 text edit.
3. The code comment and the story cite "DESK_DECISIONS row 229", which is a file line number and moves if rows are
   inserted. The bold title ("D4/D5: the five design questions accepted as recommended") is stable. Prefer it.

Evidence labels: all findings above are strong evidence (code read and tests run), except "prefer the bold title",
which is reasoning only.

## Addendum 1: ac966350 (F4 text amended)

**Verdict: PASS. It may merge, after the full gates on the final merged tree (merge procedure).**

Checked myself:
- **Diff from e5906769 to ac966350, outside `main`'s own changes.** It touches only `docs/stories/F-ai-layer.md`
  (F4) and response 256. `fno/`, `tests/` and `D-playbook-decisions.md` are unchanged from b49abdde (`git diff
  --stat` is empty). The code verdict and my four mutations above still hold.
- **F4 against the owner's decision of 16 Oct** ("D4/D5: the five design questions accepted as recommended", item
  (4), "no overrides on paper"):
  - The override record and the override sample in the audit are removed.
  - Criterion 3 now reads "no override of a judge verdict or a C4 failure on any paper decision ... refused (D3), and
    nothing in F4 writes one".
  - The test plan no longer mentions overrides.
  - S1's safety stop and C2's brake restart are named as outside F4, which is correct: the brake restart is a risk
    control (JUDGE.md, "Brake restarts").
- **No contradiction remains:** I grep'd F4's section for "override", and every remaining mention says "none" or names
  the C2 file.

Notes, not findings:
1. `docs/stories/S-scoreboards.md:63` still lists "overrides (F4)" as an input, as the builder flagged. That is S2's
   owner's text and should go with minor 1 above (S2's stale `RecordedOwnerOverride`).
2. The O11 plan (judge 305) proposes dropping F4 altogether. This amendment keeps F4 without overrides. The two can
   coexist only once the owner decides whether F4 stays.
