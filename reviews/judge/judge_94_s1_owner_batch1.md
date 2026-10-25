# Judge 94: S1 owner batch 1: `story/s1-owner-batch1` b6dcc65 (lane 1, response 93)

**What I did:**
- read the full diff;
- checked each decided value against the owner's rows of 14 Oct in `docs/DESK_DECISIONS.md` and the owner's words in
  `conversations/2026-10-14.md`;
- planted 8 mutations;
- ran `evaluation check` and `evaluation check --decided`;
- ran the full gates on a trial merge with `main`.

## Gates

On a trial merge with `main`:
- 3,158 passed with `FNO_SLACK_BOT_TOKEN` unset;
- `ruff check`, `ruff format --check` and `check_imports` are clean.

`python -m fno evaluation check` exits 0. `--decided` exits 2, because 13 items are still open.

## Decided values against the owner's words

| Item | Owner (log line 1041-1045, DESK_DECISIONS rows 83-87) | Protocol on the branch | Result |
|---|---|---|---|
| `frozen_files` and `reporting_per_version` | "1. When do trades start counting? => A" (row 83: option A, freeze only once the S2, S3, F8 and F9 code exists) | Scoring code joins the hashed list before the freeze; version 1 waits for it; the hashes-only version 2 is removed; earlier decisions are pilot evidence | MET |
| `uncertainty_criterion` | "2. How long ... => A" (row 84: 120 trading days, against the recommendation; t-check still asked) | 120 days kept; the weakness stated; the t-based check "with the owner, not part of this rule" | MET (see should-fix 1) |
| `ai_cost_allocation` | "3 ... => A" (row 85: usage share, development apart) | Status decided; value unchanged from the proposal | MET |
| `catastrophic_loss_strategy` | "4. Pause a strategy once its total losses reach Rs 30,000, even if no single trade lost Rs 10,000? => Yes" (row 86) | Second rule: "the version's cumulative realised C1 net reaches minus 3 times its `catastrophic_loss_rs`" | Value MET; **the counting window does not match the code: must-fix** |
| `risk.stressed_margin` | "5. Crash buffer for margin. => A" (row 87: 1.45 by hand, source response 77) | `config.yaml`: multiplier 1.45, source response 77, as_of 2026-10-14, max_age 30 | MET |

## Code

| Criterion | Result | Evidence |
|---|---|---|
| Cumulative pause: approved version, book trades, all books together, at or below −3 × cap | MET | `cumulative_losses`; tests at the exact boundary and one paisa short. My plants were all caught: caps 4 (3 failed); `<=` to `<` (1); window removed (1); shadow trades counted for a paper version (1); shadow paused or alerted on any day (1); call removed from `run.py` (3). |
| A shadow is alerted only on a closing day, never paused | MET | Test; my plant caught. |
| Stressed margin valid 14 Oct to 13 Nov, refused on 14 Nov | MET | Wiring test on the repository's own config. My plants were caught: `max_age` 31 (2 failed); factor 1.4 (2 failed). |
| Test edits are honest | MET | `test_completeness` now expects exactly the five decided items to be decided, and the open count derives from them. The old "every item undecided" test was correct only for a full draft. `test_manager` keeps "refused until margin rows are entered" and adds the factor-validity tests. Nothing was weakened. |
| A re-approval cannot reset the count without the owner | MET (by D1) | `paper -> paper` is not an allowed change (`transitions.py`). The only way back to paper is `paused -> paper`, which is `OWNER_ONLY`. So no agent can restart the window without a pause and an owner row in the registry. The registry is under `playbook/`, which is lane 1, so the judge sees such a row. |

## Must-fix: the decided text and the code count different losses

- **What the decided text says.** "The version's cumulative realised C1 net". The owner's question said "total losses".
- **What the code counts.** Only **book trades closed since the version's latest change to paper**, across books. Shadow
  trades are left out, and so are trades before a re-approval. This matches judge 73's rule for the per-trade cap, which
  is consistent.
- **Consequence: the count restarts at every re-approval.** A version paused at −Rs 30,000 and re-approved by the owner
  can lose another Rs 30,000 before it pauses again: Rs 60,000 in total, which is not what "total losses reach
  Rs 30,000" says. The same holds for losses taken during its shadow test.
- **Fix.** Write the counting window into the protocol's value: "book trades closed since the version's latest change
  to paper, all books together; shadow trades excluded; an owner re-approval restarts the count". Put that one sentence
  to the owner, because it is a substantive reading of "total". If the owner wants lifetime totals instead, change
  `cumulative_losses` to count every book trade of the version.
- **Recommendation (reasoning only).** The restart is defensible: the owner re-approves only after seeing the pause.
  But it must be written and decided, not left implied.

## Should-fix

1. **Record the option texts behind the "A" answers in the repository.** The owner answered "=> A" to the
   orchestrator's numbered questions. The option texts are not in `conversations/2026-10-14.md`, so "A" can be mapped
   to "120 trading days", "usage share" or "1.45" only through the orchestrator's own decision rows. These rows are
   consistent with each other and with the pushback logged at line 1057, but the owner's choice should be checkable
   from the owner's own words.
2. **State in `config.yaml` where the 1.45 multiplier comes from in response 77.** The comment says "largest
   held-position rise over three crisis windows". Fine, but name the windows or section so the next renewal on 13 Nov
   can recompute it.

## Verdict: FAIL for b6dcc65

One must-fix: the cumulative rule's counting window has to be written into the decided text and confirmed by the owner.
Everything else is correct and well tested.

## Addendum 1 (14 Oct 2026): 1dc45b5 (on top of b6dcc65; config comment at d5e1ab6)

| Item | Result | Evidence |
|---|---|---|
| Must-fix: the counting window is written into the decided text | MET | `catastrophic_loss_strategy` now reads: "The count covers the version's book trades closed since its latest change to paper, in all books together; shadow trades are excluded; an owner re-approval restarts the count". That is exactly what `cumulative_losses` does, and `test_cumulative_pause.py` pins it: my 8 plants were caught at b6dcc65, and the code is unchanged since. The owner's decision is `docs/DESK_DECISIONS.md` row 92: "Restarting a paused strategy: reset the Rs 30,000 loss count (A, recommended)". |
| Should-fix 1: option texts behind the "=> A" answers | MET | `main` 91b6b1a adds the option texts as sent to `conversations/2026-10-14.md`, including the owner's own words on item 2 ("let's start with 6 months. we can always increase that period."). Each decided value matches its option A. |
| Should-fix 2: the source of 1.45 | MET | The comment names the rule (the largest held-position margin rise, rounded up to the next 0.05), the response 77 section and the three windows: COVID 1.265; election 1.407 (BF 300, entered 5 Jun); calm 1.127. All three numbers match response 77 lines 155-157. 1.407 rounded up gives 1.45. The renewal rule is stated. |
| Gates | MET | Trial merge with `main`: 3,159 passed with the Slack token unset. `ruff check` and `check_imports` clean. `evaluation check` exits 0 and `--decided` exits 2, with 13 items open. |

Follow-up, not blocking: the owner's words for the restart decision appear only in decision row 92, which quotes them.
The conversation log does not have them yet. Log them, as 91b6b1a did for the other answers.

**Verdict: PASS for 1dc45b5.** Merge it. After the merge I check `main` and CI.

## Addendum 2 (14 Oct 2026): merge e46e3d8 MET

- **Merge.** Parents d5ddc66 and 1dc45b5. My recomputed `git merge-tree` of the two equals e46e3d8 exactly.
- **No unjudged change after it.** Nothing outside logs, judge files and decision rows has changed on `main` since
  (up to 9c6531c).
- **Owner's words logged.** The owner's restart decision is now in `conversations/2026-10-14.md` (f6baaf9), which closes
  the addendum 1 follow-up.
- **CI is green** on 9c6531c, the first push carrying the merge, and on 0895fd6.
